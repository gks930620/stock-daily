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
    """ticker -> (price_krw, category, name). USD자산은 원화 환산."""
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
        krw = float(last) if cat in KRW_CATEGORIES else (float(last) * usdkrw if usdkrw else None)
        if krw:
            out[t] = {"price_krw": krw, "category": cat, "name": d.get("name", t)}
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

    # 오늘 주문 적용 (하루 1회만)
    orders_doc = load_json(REPO / "portfolio" / "orders" / f"{today}.json", {})
    orders = orders_doc.get("orders", [])
    if today not in state.get("applied_orders", []):
        for o in orders:
            act = (o.get("action") or "").lower()
            t = o.get("ticker")
            if act == "hold" or not t:
                continue
            if t not in prices:
                print(f"  건너뜀: {t} 시세 없음", file=sys.stderr)
                continue
            p = prices[t]["price_krw"]
            name = o.get("name") or prices[t]["name"]
            if act == "buy":
                if prices[t]["category"] not in TRADABLE:
                    print(f"  건너뜀: {name} 매수불가 분류", file=sys.stderr); continue
                krw = min(float(o.get("krw", 0)), cash)
                if krw <= 0:
                    continue
                qty = krw / p
                h = holdings.setdefault(t, {"name": name, "qty": 0.0, "cost_krw": 0.0})
                h["qty"] += qty; h["cost_krw"] += krw; h["name"] = name
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
                executed.append({"action": "매도", "ticker": t, "name": name, "krw": round(proceeds), "qty": round(qty, 4), "price_krw": round(p), "reason": o.get("reason", "")})
                if h["qty"] <= 1e-9:
                    holdings.pop(t, None)
        state.setdefault("applied_orders", []).append(today)

    # 재평가
    hold_view = []
    holdings_value = 0.0
    for t, h in holdings.items():
        pr = prices.get(t, {}).get("price_krw")
        if pr is None:
            continue
        val = h["qty"] * pr
        holdings_value += val
        avg = h["cost_krw"] / h["qty"] if h["qty"] else 0
        hold_view.append({
            "ticker": t, "name": h["name"], "qty": round(h["qty"], 4),
            "price_krw": round(pr), "value_krw": round(val),
            "pl_pct": round((pr / avg - 1) * 100, 2) if avg else 0.0,
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

    # 히스토리 upsert
    hist = [h for h in state.get("history", []) if h["date"] != today]
    hist.append({"date": today, "total_value": round(total), "return_pct": round(ret_pct, 2)})
    hist.sort(key=lambda x: x["date"])

    state.update({
        "cash": round(cash), "holdings": holdings, "updated": today,
        "total_value": round(total), "holdings_value": round(holdings_value),
        "return_pct": round(ret_pct, 2), "usdkrw": round(usdkrw, 2) if usdkrw else None,
        "holdings_view": hold_view, "history": hist, "last_orders": executed,
        "last_comment": orders_doc.get("comment", ""),
        # 표시용 문자열
        "total_value_str": won(total), "cash_str": won(cash),
        "holdings_value_str": won(holdings_value), "start_capital_str": won(START_CAPITAL),
        "gain_str": ("+" if total >= START_CAPITAL else "") + won(total - START_CAPITAL),
        "days": len(hist),
    })
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
