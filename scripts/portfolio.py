"""
가상 포트폴리오 (페이퍼 트레이딩) — 1억 원, 하루 단위 매매.

체결 규칙 (룩어헤드 방지 — docs/RULES.md §3):
  · 주식/ETF: 예상글에서 주문 → "그 종목 시장의 다음 개장 시가"에 체결 (주문 시점엔 체결가를 모름)
      - 🇰🇷 한국주: 08시(kr세션) 주문 → 당일 09:00 시가 / 21시(us세션) 주문 → 다음 거래일 시가
      - 🇺🇸 미국주·ETF: 어느 세션이든 → 당일 밤(22:30 KST) 개장 시가
      - 체결 기록은 시가가 확정되는 다음 수집 실행 때 이뤄진다 (pending → fill)
  · 암호화폐·원자재(24시간 거래): 주문 즉시 그 시점 시세로 체결
  · 한국주 정수 주수, 해외 소수점 + 체결 시점 환율 기록

성향별 3인: 실행 `python portfolio.py <label> <persona>` (persona=stable|aggressive|contrarian)
상태: _data/portfolio-<persona>.json (holdings/lots/journal/pending_orders/history)
주문: portfolio/orders/<날짜>-<세션>-<persona>.json · 자산곡선: assets/portfolio/equity-<persona>.png
"""

from __future__ import annotations

import json
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
IMMEDIATE = {"crypto", "commodity"}          # 24시간 거래 → 즉시 체결
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
    today = datetime.now(KST).strftime("%Y-%m-%d")
    market = load_json(REPO / "data" / today / "market.json")
    if not market:
        print(f"market.json 없음(data/{today}) — 포트폴리오 갱신 생략", file=sys.stderr)
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

    # ── 1) 새 주문서 접수: 즉시체결(크립토·원자재) / 대기등록(주식·ETF) ──
    orders_dir = REPO / "portfolio" / "orders"
    new_files = sorted(p for p in orders_dir.glob(f"{today}-*-{persona}.json") if p.stem not in applied) if orders_dir.exists() else []
    for opath in new_files:
        doc = load_json(opath, {})
        session = doc.get("session") or (opath.stem.split("-")[-1] if opath.stem.count("-") > 2 else "")
        placed_view, immediate_trades = [], []
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

            if info["category"] in IMMEDIATE:
                # 24시간 자산 → 즉시 체결 (주문 시점 시세)
                if act == "buy":
                    cash, tr = exec_buy(holdings, cash, t, info, o.get("krw", 0),
                                        info["price_krw"], info["price_native"], usdkrw,
                                        today, session, o.get("reason", ""), "즉시(24h)")
                else:
                    cash, tr = exec_sell(holdings, cash, t, info, o.get("qty"),
                                         info["price_krw"], today, session, o.get("reason", ""), "즉시(24h)")
                if tr:
                    immediate_trades.append(tr)
            else:
                # 주식/ETF → 다음 개장 시가 체결 대기
                if info["currency"] == "KRW":
                    min_fill = today if session == "kr" else next_day(today)   # 21시 주문이면 다음 거래일 시가
                else:
                    min_fill = today                                            # 미국장은 오늘 밤 개장
                pending.append({"placed_date": today, "session": session, "action": act,
                                "ticker": t, "name": info["name"],
                                "krw": o.get("krw"), "qty": o.get("qty"),
                                "reason": o.get("reason", ""), "min_fill_date": min_fill})
                placed_view.append({"action": "매수예약" if act == "buy" else "매도예약",
                                    "name": info["name"],
                                    "detail": (won(o.get("krw", 0)) + "원 · " if act == "buy" else "") + "다음 개장 시가 체결 대기 — " + o.get("reason", "")})
        applied.append(opath.stem)
        journal.append({"date": today, "session": session, "comment": doc.get("comment", ""),
                        "placed": placed_view, "trades": immediate_trades})

    # ── 2) 체결 패스: 개장 시가가 확정된 대기 주문 체결 ──
    fills = []
    for od in list(pending):
        info = prices.get(od["ticker"])
        if not info or not info.get("open_krw"):
            continue
        if (info.get("data_date") or "") < od["min_fill_date"]:
            continue  # 아직 그 시장이 안 열림 (시가 미확정)
        basis = f"{info['data_date']} 개장 시가"
        if od["action"] == "buy":
            cash, tr = exec_buy(holdings, cash, od["ticker"], info, od.get("krw", 0),
                                info["open_krw"], info["open_native"], usdkrw,
                                today, od["session"], od.get("reason", ""), basis)
        else:
            cash, tr = exec_sell(holdings, cash, od["ticker"], info, od.get("qty"),
                                 info["open_krw"], today, od["session"], od.get("reason", ""), basis)
        pending.remove(od)
        if tr:
            tr["placed_date"] = od["placed_date"]
            fills.append(tr)
    if fills:
        journal.append({"date": today, "session": "fill",
                        "comment": "예약 주문 개장 시가 체결", "placed": [], "trades": fills})

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

    # 대기 주문 표시용
    pending_view = [{**od, "krw_str": won(od["krw"]) if od.get("krw") else None,
                     "session_label": SESSION_LABEL.get(od["session"], od["session"]),
                     "action_label": "매수" if od["action"] == "buy" else "매도"} for od in pending]

    # ── 4) 히스토리 (일별 스냅샷) — 매일 18시(krclose) 평가만 '확정' 기록 ──
    hist = state.get("history", [])
    finalize = (label == "krclose") or not hist          # 18시 확정 / 최초 1회 시드
    prev_marks = [h for h in hist if h["date"] != today]
    prev_total = prev_marks[-1]["total_value"] if prev_marks else START_CAPITAL
    day_chg_pct = round((total / prev_total - 1) * 100, 2) if prev_total else 0.0
    if finalize:
        hist = prev_marks + [{
            "date": today, "total_value": round(total), "total_value_str": won(total),
            "return_pct": round(ret_pct, 2), "day_chg_pct": day_chg_pct, "cash": round(cash),
            "asof": "18:00 평가" if label == "krclose" else "개설일 시드",
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
        "eval_note": "일별 평가 확정 = 매일 18:00 KST (한국주 = 당일 종가 · 미국주 = 간밤 종가)",
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
    ax.set_title(f"[{pmeta['name']}] 가상 포트폴리오 자산 추이 (매일 18시 평가)  ·  {total:,.0f}원 ({ret_pct:+.2f}%)", fontsize=13, fontweight="bold")
    ax.yaxis.set_major_formatter(lambda x, _: f"{x/1e8:.2f}억")
    ax.legend(fontsize=9); ax.grid(alpha=0.25)
    if len(dates) > 12:
        ax.set_xticks(range(0, len(dates), max(1, len(dates) // 10)))
    fig.autofmt_xdate(rotation=0)
    fig.tight_layout()
    fig.savefig(chart_dir / f"equity-{persona}.png", dpi=110)
    plt.close(fig)

    print(f"[{persona}] 총 {total:,.0f}원 ({ret_pct:+.2f}%) · 현금 {cash:,.0f} · 보유 {len(hold_view)} · 체결 {len(fills)}건 · 대기 {len(pending)}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
