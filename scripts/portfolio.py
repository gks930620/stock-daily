"""
가상 포트폴리오 (페이퍼 트레이딩) — 1억 원으로 시작.

- Claude가 매일 분석 후 `portfolio/orders/YYYY-MM-DD.json`에 매수/매도/유지 주문을 기록한다.
- 이 스크립트가 그 주문을 실제 시세(오늘 market.json)로 적용하고, 전체 자산을 재평가한 뒤
  자산 곡선(equity curve) 차트를 만든다.
- 상태 파일: `_data/portfolio.json` (Jekyll이 사이트에서 읽어 표시 + 다음 날 이어감)

통화: 포트폴리오는 원화(KRW). 미국주·ETF·코인·원자재는 USD → 원/달러(KRW=X)로 환산.
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
START_CAPITAL = 100_000_000  # 1억 원
KRW_CATEGORIES = {"kr_index", "kr_stock"}
TRADABLE = {"us_stock", "kr_stock", "us_sector", "crypto", "commodity"}


def load_json(path: Path, default=None):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def won(n):
    return f"{round(n):,}"


def eok(n):
    return f"{n/1e8:.3f}억"


def price_map(market: dict):
    """ticker -> 시세 정보. USD자산은 원화 환산 + 원 통화 가격 보존."""
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
        krw = float(last) if is_krw else (float(last) * usdkrw if usdkrw else None)
        if krw:
            out[t] = {
                "price_krw": krw, "price_native": float(last),
                "currency": "KRW" if is_krw else "USD",
                "category": cat, "name": d.get("name", t),
                "data_date": d.get("data_date"),
            }
    return out, usdkrw


def main() -> int:
    today = datetime.now(KST).strftime("%Y-%m-%d")

    market = load_json(REPO / "data" / today / "market.json")
    if not market:
        print(f"market.json 없음(data/{today}) — 포트폴리오 갱신 생략", file=sys.stderr)
        return 0
    prices, usdkrw = price_map(market)

    state_path = REPO / "_data" / "portfolio.json"
    state = load_json(state_path)
    if not state:
        state = {
            "start_date": today, "start_capital": START_CAPITAL, "currency": "KRW",
            "cash": START_CAPITAL, "holdings": {}, "applied_orders": [], "history": [],
        }
        print(f"포트폴리오 신규 개설: {START_CAPITAL:,}원 ({today})")

    # holdings 내부 저장형: {ticker: {name, qty, cost_krw}}
    holdings = state.get("holdings", {})
    cash = float(state.get("cash", START_CAPITAL))
    executed = []

    # 오늘 주문 적용 — 세션별 파일(YYYY-MM-DD.json / -kr.json / -us.json) 모두, 각 1회만
    orders_dir = REPO / "portfolio" / "orders"
    applied = state.setdefault("applied_orders", [])
    last_comment = ""
    pending_files = sorted(p for p in orders_dir.glob(f"{today}*.json") if p.stem not in applied) if orders_dir.exists() else []
    journal = state.setdefault("journal", [])  # 매매 일지: 세션별 결정(매수/매도/유지) 전체 기록
    for opath in pending_files:
        orders_doc = load_json(opath, {})
        orders = orders_doc.get("orders", [])
        if orders_doc.get("comment"):
            last_comment = orders_doc["comment"]
        session_executed_start = len(executed)
        for o in orders:
            act = (o.get("action") or "").lower()
            t = o.get("ticker")
            if act == "hold" or not t:
                continue
            if t not in prices:
                print(f"  건너뜀: {t} 시세 없음", file=sys.stderr)
                continue
            info = prices[t]
            p = info["price_krw"]
            name = o.get("name") or info["name"]
            session_tag = orders_doc.get("session") or (opath.stem.split("-")[-1] if opath.stem.count("-") > 2 else "")
            if act == "buy":
                if info["category"] not in TRADABLE:
                    print(f"  건너뜀: {name} 매수불가 분류", file=sys.stderr); continue
                budget = min(float(o.get("krw", 0)), cash)
                if budget <= 0:
                    continue
                if info["currency"] == "KRW":          # 한국 주식: 정수 주수만 (잔액은 현금 유지)
                    qty = int(budget // p)
                    if qty < 1:
                        print(f"  건너뜀: {name} 예산으로 1주 미만", file=sys.stderr); continue
                    krw = qty * p
                else:                                    # 해외 자산: 소수점 매수 허용
                    qty = budget / p
                    krw = budget
                h = holdings.setdefault(t, {"name": name, "qty": 0.0, "cost_krw": 0.0, "lots": []})
                h["qty"] += qty; h["cost_krw"] += krw; h["name"] = name
                h.setdefault("lots", []).append({
                    "date": today, "session": session_tag, "qty": round(qty, 4),
                    "price_krw": round(p), "price_native": round(info["price_native"], 2),
                    "currency": info["currency"], "krw": round(krw),
                    "fx": round(usdkrw, 2) if info["currency"] == "USD" and usdkrw else None,
                    "price_date": info.get("data_date"),
                })
                cash -= krw
                executed.append({"action": "매수", "ticker": t, "name": name, "krw": round(krw), "qty": round(qty, 4), "price_krw": round(p), "reason": o.get("reason", "")})
            elif act == "sell":
                h = holdings.get(t)
                if not h or h["qty"] <= 0:
                    continue
                qty = float(o.get("qty", h["qty"]))
                qty = min(qty, h["qty"])
                proceeds = qty * p
                ratio = qty / h["qty"] if h["qty"] else 0
                h["cost_krw"] *= (1 - ratio); h["qty"] -= qty; cash += proceeds
                remain = qty                              # 매수 내역(lots)에서 FIFO 차감
                for lot in list(h.get("lots", [])):
                    if remain <= 1e-9:
                        break
                    take = min(lot["qty"], remain)
                    lot["qty"] = round(lot["qty"] - take, 4)
                    lot["krw"] = round(lot["qty"] * lot["price_krw"])
                    remain -= take
                    if lot["qty"] <= 1e-9:
                        h["lots"].remove(lot)
                executed.append({"action": "매도", "ticker": t, "name": name, "krw": round(proceeds), "qty": round(qty, 4), "price_krw": round(p), "reason": o.get("reason", "")})
                if h["qty"] <= 1e-9:
                    holdings.pop(t, None)
        applied.append(opath.stem)
        session_trades = executed[session_executed_start:]
        for tr in session_trades:
            tr["krw_str"] = won(tr["krw"])
        journal.append({
            "date": today,
            "session": orders_doc.get("session") or (opath.stem.split("-")[-1] if "-kr" in opath.stem or "-us" in opath.stem else ""),
            "comment": orders_doc.get("comment", ""),
            "trades": session_trades,
        })

    # 재평가
    hold_view = []
    holdings_value = 0.0
    for t, h in holdings.items():
        info = prices.get(t)
        if not info:
            continue
        pr = info["price_krw"]
        val = h["qty"] * pr
        holdings_value += val
        avg = h["cost_krw"] / h["qty"] if h["qty"] else 0
        is_usd = info["currency"] == "USD"
        lots_view = []
        for lot in h.get("lots", []):
            lots_view.append({**lot,
                "krw_str": won(lot["krw"]), "price_krw_str": won(lot["price_krw"]),
                "native_str": (f"${lot['price_native']:,.2f}" if lot.get("currency") == "USD" else None)})
        hold_view.append({
            "ticker": t, "name": h["name"], "qty": round(h["qty"], 4),
            "currency": info["currency"],
            "avg_krw": round(avg), "avg_str": won(avg),
            "price_krw": round(pr), "price_str": won(pr),
            "price_native_str": (f"${info['price_native']:,.2f}" if is_usd else None),
            "price_date": info.get("data_date"),
            "value_krw": round(val),
            "pl_pct": round((pr / avg - 1) * 100, 2) if avg else 0.0,
            "lots": lots_view,
        })
    hold_view.sort(key=lambda x: x["value_krw"], reverse=True)
    total = cash + holdings_value
    ret_pct = (total / START_CAPITAL - 1) * 100
    for hv in hold_view:
        hv["weight_pct"] = round(hv["value_krw"] / total * 100, 1) if total else 0
        hv["value_str"] = won(hv["value_krw"])
        hv["price_str"] = won(hv["price_krw"])
    for ex in executed:
        ex["krw_str"] = won(ex["krw"])

    # 히스토리 upsert (일별 스냅샷: 총자산·일간변동·현금·보유요약)
    hist = [h for h in state.get("history", []) if h["date"] != today]
    prev_total = hist[-1]["total_value"] if hist else START_CAPITAL
    day_chg_pct = round((total / prev_total - 1) * 100, 2) if prev_total else 0.0
    hist.append({
        "date": today, "total_value": round(total), "total_value_str": won(total),
        "return_pct": round(ret_pct, 2), "day_chg_pct": day_chg_pct,
        "cash": round(cash),
        "holdings": [{"name": hv["name"], "value_str": hv["value_str"], "weight_pct": hv["weight_pct"], "pl_pct": hv["pl_pct"]} for hv in hold_view],
    })
    hist.sort(key=lambda x: x["date"])

    state.update({
        "cash": round(cash), "holdings": holdings, "updated": today,
        "total_value": round(total), "holdings_value": round(holdings_value),
        "return_pct": round(ret_pct, 2), "usdkrw": round(usdkrw, 2) if usdkrw else None,
        "holdings_view": hold_view, "history": hist,
        # 표시용 문자열
        "total_value_str": won(total), "cash_str": won(cash),
        "holdings_value_str": won(holdings_value), "start_capital_str": won(START_CAPITAL),
        "gain_str": ("+" if total >= START_CAPITAL else "") + won(total - START_CAPITAL),
        "cash_weight_pct": round(cash / total * 100, 1) if total else 0,
        "day_chg_pct": day_chg_pct,
        "days": len(hist),
        "priced_at": market.get("generated_at_kst", ""),   # 현재가 기준 시각 (수집 시각)
    })
    state["journal_view"] = list(reversed(journal))     # 최신이 위로 (사이트 표시용)
    state["history_view"] = list(reversed(hist))
    if pending_files:  # 새 주문이 있었을 때만 '최근 매매' 표시 갱신 (빈 실행이 지우지 않게)
        state["last_orders"] = executed
        state["last_comment"] = last_comment
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # 자산 곡선 차트
    chart_dir = REPO / "assets" / "portfolio"
    chart_dir.mkdir(parents=True, exist_ok=True)
    if len(hist) >= 1:
        dates = [h["date"][5:] for h in hist]  # MM-DD
        vals = [h["total_value"] for h in hist]
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(dates, vals, color="#175cd3", linewidth=2, marker="o", markersize=4)
        ax.axhline(START_CAPITAL, color="#94a3b8", linestyle="--", linewidth=1, label="시작 (1억)")
        ax.fill_between(range(len(dates)), START_CAPITAL, vals, alpha=0.08, color="#175cd3")
        ax.set_title(f"가상 포트폴리오 자산 추이  ·  {total:,.0f}원 ({ret_pct:+.2f}%)", fontsize=13, fontweight="bold")
        ax.yaxis.set_major_formatter(lambda x, _: f"{x/1e8:.2f}억")
        ax.legend(fontsize=9); ax.grid(alpha=0.25)
        if len(dates) > 12:
            ax.set_xticks(range(0, len(dates), max(1, len(dates)//10)))
        fig.autofmt_xdate(rotation=0)
        fig.tight_layout()
        fig.savefig(chart_dir / "equity.png", dpi=110)
        plt.close(fig)

    print(f"포트폴리오 갱신: 총 {total:,.0f}원 ({ret_pct:+.2f}%) · 현금 {cash:,.0f} · 보유 {len(hold_view)}종목 · 오늘체결 {len(executed)}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
