"""
가상 포트폴리오 (페이퍼 트레이딩) — 1억 원, 하루 단위 매매.

체결 규칙 (docs/RULES.md §3):
  · **장이 열려 있는 동안** AI가 판단하고 리포트를 낸다 → 주문은 **리포트 발행 시점의 시장가로 즉시 체결**.
      - 🇰🇷 한국장: ~15:00 리포트 → 독자는 15:00~15:30(마감 전)에 같은 가격대로 매수 가능
      - 🇺🇸 미국장: ~23:40 리포트(장중) → 독자는 그 자리에서 매수 가능
  · **핵심은 실행 가능성**: 리포트를 본 사람이 30분 안에 시장가로 살 수 있어야 한다.
  · 룩어헤드 없음: 체결가는 AI가 판단을 끝낸 뒤 **다시 수집한** 시세(AI가 못 본 가격)이고,
    손익은 그 이후 가격으로 결정된다.
  · 주식·ETF 정수 주수 / 암호화폐·원자재 소수 + 체결 시점 환율 기록.

성향별 3인: 실행 `python portfolio.py <label> <persona>` (persona=stable|aggressive|contrarian)
상태: _data/portfolio-<persona>.json (holdings/lots/journal/pending_orders/history)
주문: portfolio/orders/<날짜>-<세션>-<persona>.json · 자산곡선: assets/portfolio/equity-<persona>.png
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as _fm

for _f in ("Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic"):
    if _f in {f.name for f in _fm.fontManager.ttflist}:
        matplotlib.rcParams["font.family"] = _f
        break
matplotlib.rcParams["axes.unicode_minus"] = False

KST = timezone(timedelta(hours=9))
REPO = Path(__file__).resolve().parent.parent
START_CAPITAL = 100_000_000
KRW_CATEGORIES = {"kr_index", "kr_stock"}
TRADABLE = {"us_stock", "kr_stock", "us_sector", "crypto", "commodity"}
IMMEDIATE = {"crypto", "commodity"}          # 24시간 거래 → 언제든 그 시점 시세로 체결
# 세션별 거래 가능 시장 — 자기 시장이 방금 마감한 종목만 거래한다.
# (예: 한국장 마감 16시에 미국 ETF를 사면 며칠 전 미국 종가에 체결되는데, 그 시각엔 그 가격에 살 수 없다)
SESSION_CATS = {"kr": {"kr_stock"}, "us": {"us_stock", "us_sector"}}
SESSION_LABEL = {"kr": "🇰🇷 아침", "us": "🇺🇸 저녁", "fill": "⚡ 체결", "": ""}

# 성향별 AI 투자자 3명 — 각자 독립 계좌(_data/portfolio-<id>.json)
PERSONAS = {
    "stable":     {"name": "안정형",   "emoji": "🛡️", "tag": "가치·방어 — 저평가 우량주·배당, 현금 넉넉, 손실 최소 우선"},
    "aggressive": {"name": "공격형",   "emoji": "🚀", "tag": "성장·모멘텀 — 주도주 추종, 집중 투자, 현금 최소"},
    "contrarian": {"name": "역발상형", "emoji": "🎯", "tag": "컨트래리안 — 과매도·낙폭과대를 남들이 팔 때 매수"},
}

# 24시간 자산(암호화폐·원자재) 표시 단위 — 나머지 주식·ETF는 "주"
UNIT_OVERRIDE = {"GC=F": "oz", "MGC=F": "oz", "SI=F": "oz", "CL=F": "bbl", "BZ=F": "bbl",
                 "BTC-USD": "BTC", "ETH-USD": "ETH"}


def unit_of(ticker: str, category: str) -> str:
    if ticker in UNIT_OVERRIDE:
        return UNIT_OVERRIDE[ticker]
    if category == "crypto":
        return "개"
    if category == "commodity":
        return "단위"
    return "주"          # 주식·ETF


def qn(q):
    """정수면 int(64), 아니면 소수 4자리(1.9908) — '64.0주' 방지."""
    q = float(q)
    return int(q) if q.is_integer() else round(q, 4)


def load_json(path: Path, default=None):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def won(n):
    return f"{round(n):,}"


def next_day(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def price_map(market: dict):
    inst = market.get("instruments", {})
    usdkrw = None
    if "KRW=X" in inst and inst["KRW=X"].get("last"):
        usdkrw = float(inst["KRW=X"]["last"])
    out = {}
    for t, d in inst.items():
        last = d.get("last")
        if last is None:
            continue
        cat = d.get("category", "")
        is_krw = cat in KRW_CATEGORIES
        fx = 1.0 if is_krw else usdkrw
        if not fx:
            continue
        out[t] = {
            "price_krw": float(last) * fx,
            "price_native": float(last),
            "open_native": float(d["open"]) if d.get("open") else None,
            "open_krw": float(d["open"]) * fx if d.get("open") else None,
            "currency": "KRW" if is_krw else "USD",
            "category": cat, "name": d.get("name", t),
            "data_date": d.get("data_date"),
        }
    return out, usdkrw


def exec_buy(holdings, cash, t, info, budget, price_krw, price_native, usdkrw, today, session, reason, basis):
    """매수 체결. (성공 시 갱신된 cash, trade기록) 반환. 실패 시 (cash, None)."""
    budget = min(float(budget), cash)
    if budget <= 0:
        return cash, None
    if info["category"] in IMMEDIATE:
        # 24시간 자산(암호화폐·원자재): 소수 단위 매수가 현실적
        qty = budget / price_krw
        krw = budget
    else:
        # 주식·ETF(한국·미국 공통): 정수 주수만, 잔액은 현금 유지
        qty = int(budget // price_krw)
        if qty < 1:
            return cash, None
        krw = qty * price_krw
    h = holdings.setdefault(t, {"name": info["name"], "qty": 0.0, "cost_krw": 0.0, "lots": []})
    h["qty"] += qty; h["cost_krw"] += krw; h["name"] = info["name"]
    h.setdefault("lots", []).append({
        "date": today, "session": session, "qty": qn(qty),
        "price_krw": round(price_krw), "price_native": round(price_native, 2),
        "currency": info["currency"], "krw": round(krw),
        "fx": round(usdkrw, 2) if info["currency"] == "USD" and usdkrw else None,
        "price_date": info.get("data_date"), "basis": basis,
    })
    trade = {"action": "매수", "ticker": t, "name": info["name"], "krw": round(krw), "krw_str": won(krw),
             "qty": qn(qty), "price_krw": round(price_krw), "basis": basis, "reason": reason}
    return cash - krw, trade


def exec_sell(holdings, cash, t, info, qty_req, price_krw, today, session, reason, basis):
    h = holdings.get(t)
    if not h or h["qty"] <= 0:
        return cash, None
    qty = min(float(qty_req) if qty_req else h["qty"], h["qty"])
    proceeds = qty * price_krw
    ratio = qty / h["qty"] if h["qty"] else 0
    h["cost_krw"] *= (1 - ratio); h["qty"] -= qty
    remain = qty
    for lot in list(h.get("lots", [])):
        if remain <= 1e-9:
            break
        take = min(lot["qty"], remain)
        lot["qty"] = round(lot["qty"] - take, 4)
        lot["krw"] = round(lot["qty"] * lot["price_krw"])
        remain -= take
        if lot["qty"] <= 1e-9:
            h["lots"].remove(lot)
    if h["qty"] <= 1e-9:
        holdings.pop(t, None)
    trade = {"action": "매도", "ticker": t, "name": info["name"], "krw": round(proceeds), "krw_str": won(proceeds),
             "qty": qn(qty), "price_krw": round(price_krw), "basis": basis, "reason": reason}
    return cash + proceeds, trade


def main() -> int:
    # 인자: <label> <persona>
    #   label   = morning/krclose/uspre (krclose=18시 일별평가 확정)
    #   persona = stable|aggressive|contrarian (성향별 독립 계좌)
    label = sys.argv[1] if len(sys.argv) > 1 else None
    persona = sys.argv[2] if len(sys.argv) > 2 else "stable"
    if persona not in PERSONAS:
        print(f"알 수 없는 성향: {persona} — {list(PERSONAS)}", file=sys.stderr)
        return 1
    pmeta = PERSONAS[persona]
    # 재생(replay)용 오버라이드: PF_TODAY(체결 기준일)·PF_MARKET(시세 스냅샷 경로)
    today = os.environ.get("PF_TODAY") or datetime.now(KST).strftime("%Y-%m-%d")
    mfile = os.environ.get("PF_MARKET")
    market = load_json(Path(mfile)) if mfile else load_json(REPO / "data" / today / "market.json")
    if not market:
        print(f"market.json 없음({mfile or 'data/'+today+'/market.json'}) — 포트폴리오 갱신 생략", file=sys.stderr)
        return 0
    prices, usdkrw = price_map(market)

    state_path = REPO / "_data" / f"portfolio-{persona}.json"
    state = load_json(state_path)
    if not state:
        state = {"start_date": today, "start_capital": START_CAPITAL, "currency": "KRW",
                 "cash": START_CAPITAL, "holdings": {}, "applied_orders": [],
                 "pending_orders": [], "journal": [], "history": []}
        print(f"[{persona}] 포트폴리오 신규 개설: {START_CAPITAL:,}원 ({today})")

    holdings = state.get("holdings", {})
    cash = float(state.get("cash", START_CAPITAL))
    applied = state.setdefault("applied_orders", [])
    pending = state.setdefault("pending_orders", [])
    journal = state.setdefault("journal", [])

    # ── 1) 새 주문서 접수 → 리포트 시점 시장가로 즉시 체결 ──
    # (AI 판단이 끝난 뒤 시세를 다시 수집해서 그 가격으로 체결 → AI가 못 본 가격이라 룩어헤드 없음.
    #  장중이라 리포트를 본 사람이 같은 가격대로 실제 매수 가능하다.)
    for od_unused in list(pending):
        pending.remove(od_unused)          # 구방식 잔여 대기주문 정리(있으면)
    orders_dir = REPO / "portfolio" / "orders"
    new_files = sorted(p for p in orders_dir.glob(f"{today}-*-{persona}.json") if p.stem not in applied) if orders_dir.exists() else []
    for opath in new_files:
        doc = load_json(opath, {})
        session = doc.get("session") or (opath.stem.split("-")[-1] if opath.stem.count("-") > 2 else "")
        placed_view, trades = [], []
        for o in doc.get("orders", []):
            act = (o.get("action") or "").lower()
            t = o.get("ticker")
            if act == "hold" or not t:
                if act == "hold":
                    placed_view.append({"action": "유지", "name": "-", "detail": o.get("reason", "")})
                continue
            info = prices.get(t)
            if not info:
                print(f"  건너뜀: {t} 시세 없음", file=sys.stderr); continue
            if act == "buy" and info["category"] not in TRADABLE:
                print(f"  건너뜀: {info['name']} 매수불가 분류", file=sys.stderr); continue
            # 세션 ≠ 그 종목의 시장이면 거래 불가 (24시간 자산은 어느 세션이든 허용)
            cat = info["category"]
            if cat not in IMMEDIATE and session in SESSION_CATS and cat not in SESSION_CATS[session]:
                print(f"  건너뜀: {info['name']} — '{session}' 세션에선 거래 불가(그 시장은 마감 종가가 오래됨)", file=sys.stderr)
                continue
            basis = f"{info.get('data_date')} 리포트 시점 시장가" if cat not in IMMEDIATE else "즉시(24h)"
            if act == "buy":
                cash, tr = exec_buy(holdings, cash, t, info, o.get("krw", 0),
                                    info["price_krw"], info["price_native"], usdkrw,
                                    today, session, o.get("reason", ""), basis)
            else:
                cash, tr = exec_sell(holdings, cash, t, info, o.get("qty"),
                                     info["price_krw"], today, session, o.get("reason", ""), basis)
            if tr:
                trades.append(tr)
        applied.append(opath.stem)
        journal.append({"date": today, "session": session, "comment": doc.get("comment", ""),
                        "placed": placed_view, "trades": trades})

    # ── 3) 재평가 ──
    hold_view, holdings_value = [], 0.0
    for t, h in holdings.items():
        info = prices.get(t)
        if not info:
            continue
        pr = info["price_krw"]
        val = h["qty"] * pr
        holdings_value += val
        avg = h["cost_krw"] / h["qty"] if h["qty"] else 0
        is_usd = info["currency"] == "USD"
        cost_native = sum(l["qty"] * l["price_native"] for l in h.get("lots", [])) if is_usd else 0
        avg_native = cost_native / h["qty"] if (is_usd and h["qty"]) else 0
        lots_view = [{**lot, "qty": qn(lot["qty"]), "krw_str": won(lot["krw"]), "price_krw_str": won(lot["price_krw"]),
                      "native_str": (f"${lot['price_native']:,.2f}" if lot.get("currency") == "USD" else None)}
                     for lot in h.get("lots", [])]
        pl_krw = val - h["cost_krw"]
        hold_view.append({
            "ticker": t, "name": h["name"], "qty": qn(h["qty"]),
            "unit": unit_of(t, info["category"]), "currency": info["currency"],
            "cost_str": won(h["cost_krw"]),
            "pl_krw_str": ("+" if pl_krw >= 0 else "") + won(pl_krw),
            "avg_krw": round(avg), "avg_str": won(avg),
            "avg_native_str": (f"${avg_native:,.2f}" if is_usd and avg_native else None),
            "price_krw": round(pr), "price_str": won(pr),
            "price_native_str": (f"${info['price_native']:,.2f}" if is_usd else None),
            "price_date": info.get("data_date"), "value_krw": round(val),
            "pl_pct": round((pr / avg - 1) * 100, 2) if avg else 0.0,
            "lots": lots_view,
        })
    hold_view.sort(key=lambda x: x["value_krw"], reverse=True)
    total = cash + holdings_value
    ret_pct = (total / START_CAPITAL - 1) * 100
    for hv in hold_view:
        hv["weight_pct"] = round(hv["value_krw"] / total * 100, 1) if total else 0
        hv["value_str"] = won(hv["value_krw"])

    # 대기 주문 없음(종가 즉시체결) — 페이지 호환 위해 빈 목록 유지
    pending_view = []

    # ── 4) 히스토리 (일별 스냅샷) — 매 실행(장 마감 후 종가)마다 확정 기록 ──
    hist = state.get("history", [])
    finalize = True                                       # 실행 시점이 이미 종가 → 항상 확정
    prev_marks = [h for h in hist if h["date"] != today]
    prev_total = prev_marks[-1]["total_value"] if prev_marks else START_CAPITAL
    day_chg_pct = round((total / prev_total - 1) * 100, 2) if prev_total else 0.0
    if finalize:
        hist = prev_marks + [{
            "date": today, "total_value": round(total), "total_value_str": won(total),
            "return_pct": round(ret_pct, 2), "day_chg_pct": day_chg_pct, "cash": round(cash),
            "asof": {"kr": "🇰🇷 장중 리포트 시점", "us": "🇺🇸 장중 리포트 시점"}.get(label, "리포트 시점"),
            "holdings": [{"name": hv["name"], "value_str": hv["value_str"], "weight_pct": hv["weight_pct"], "pl_pct": hv["pl_pct"]} for hv in hold_view],
        }]
        hist.sort(key=lambda x: x["date"])

    state.update({
        "cash": round(cash), "holdings": holdings, "updated": today,
        "total_value": round(total), "holdings_value": round(holdings_value),
        "return_pct": round(ret_pct, 2), "usdkrw": round(usdkrw, 2) if usdkrw else None,
        "holdings_view": hold_view, "history": hist,
        "pending_orders": pending, "pending_view": pending_view,
        "total_value_str": won(total), "cash_str": won(cash),
        "holdings_value_str": won(holdings_value), "start_capital_str": won(START_CAPITAL),
        "gain_str": ("+" if total >= START_CAPITAL else "") + won(total - START_CAPITAL),
        "cash_weight_pct": round(cash / total * 100, 1) if total else 0,
        "day_chg_pct": day_chg_pct, "days": len(hist),
        "priced_at": market.get("generated_at_kst", ""),
        "eval_note": "AI가 장중에 판단·리포트 발행 → 그 시점 시장가로 체결 (🇰🇷 ~15:00 · 🇺🇸 ~23:40). 리포트를 본 사람이 30분 안에 같은 가격대로 실제 매수 가능한 시각. 손익은 이후 시세로 결정",
        "persona": persona, "persona_name": pmeta["name"],
        "persona_emoji": pmeta["emoji"], "persona_tag": pmeta["tag"],
    })
    state["journal_view"] = list(reversed(journal))
    state["history_view"] = list(reversed(hist))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 5) 자산 곡선 ──
    chart_dir = REPO / "assets" / "portfolio"
    chart_dir.mkdir(parents=True, exist_ok=True)
    dates = [h["date"][5:] for h in hist]
    vals = [h["total_value"] for h in hist]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(dates, vals, color="#175cd3", linewidth=2, marker="o", markersize=4)
    ax.axhline(START_CAPITAL, color="#94a3b8", linestyle="--", linewidth=1, label="시작 (1억)")
    ax.fill_between(range(len(dates)), START_CAPITAL, vals, alpha=0.08, color="#175cd3")
    ax.set_title(f"[{pmeta['name']}] 가상 포트폴리오 자산 추이 (장 마감 종가 평가)  ·  {total:,.0f}원 ({ret_pct:+.2f}%)", fontsize=13, fontweight="bold")
    ax.yaxis.set_major_formatter(lambda x, _: f"{x/1e8:.2f}억")
    ax.legend(fontsize=9); ax.grid(alpha=0.25)
    if len(dates) > 12:
        ax.set_xticks(range(0, len(dates), max(1, len(dates) // 10)))
    fig.autofmt_xdate(rotation=0)
    fig.tight_layout()
    fig.savefig(chart_dir / f"equity-{persona}.png", dpi=110)
    plt.close(fig)

    print(f"[{persona}] 총 {total:,.0f}원 ({ret_pct:+.2f}%) · 현금 {cash:,.0f} · 보유 {len(hold_view)}종목 (당일 종가 체결)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
