"""
📉 백테스트 — 전략을 과거에 돌려본다.

  python scripts/backtest.py <전략id> [--years 3] [--split 0.7] [--refresh]

왜 이게 프로젝트의 핵심인가
  AI 4인은 하루 2표본만 만든다. 그래서 12일이 지나도 실력인지 운인지 알 수 없었다.
  전략을 **순수 함수**로 써두면 과거 수백~수천 일에 그대로 돌릴 수 있다.
  "그럴듯한 이야기"가 "몇 년치 숫자"를 이길 수는 없다.

체결은 **라이브와 같은 코드**를 쓴다
  `portfolio.py`의 `exec_buy`/`exec_sell`을 그대로 import한다. 백테스트용 체결기를
  따로 짜면 언젠가 라이브와 어긋나고, 그러면 백테스트 결과가 거짓말이 된다.

⚠️ 검증구간(out-of-sample) 규율
  전략을 만들 때 본 구간에서 잘 나오는 건 당연하다(곡선맞춤). 그래서 기간을
  **학습/검증으로 쪼개 둘 다 보여준다.** 판단은 **검증구간 숫자로만** 한다.
  검증구간이 나쁜데 학습구간이 좋다면 그건 전략이 아니라 우연을 외운 것이다.

⚠️ 라이브와 다른 점 (정직하게 알고 쓸 것)
  · 체결가가 **일봉 종가**다. 라이브는 장중 수집 스냅샷(🇰🇷 14:40 · 🇺🇸 23:30 시점)이라 기준이 다르다.
  · 수수료·세금·슬리피지 없음 (라이브 페이퍼 계좌와 동일 조건).
  · 워치리스트가 **현재 기준**이라 생존편향이 있다 — 지금 살아남은 종목만 들어 있다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from portfolio import START_CAPITAL, exec_buy, exec_sell   # noqa: E402  (라이브와 동일 체결기)
from strategies import get                                  # noqa: E402
from strategies._base import Context                        # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

CACHE = REPO / ".backtest-cache"
BENCH = "^KS11"


def universe() -> dict[str, tuple[str, str]]:
    """워치리스트에서 한국 종목·지수만 → {ticker: (name, category)}"""
    cfg = yaml.safe_load((REPO / "config" / "watchlist.yaml").read_text(encoding="utf-8")) or {}
    out = {}
    for cat, items in cfg.items():
        if cat not in ("kr_stock", "kr_index"):
            continue
        for t, n in (items or {}).items():
            out[str(t)] = (str(n), cat)
    return out


def fetch(tickers: list[str], years: int, refresh: bool) -> pd.DataFrame:
    """일봉 종가 표 (index=날짜, columns=티커). 캐시해서 재실행을 빠르게."""
    CACHE.mkdir(exist_ok=True)
    key = CACHE / f"close-{years}y-{len(tickers)}.parquet"
    if key.exists() and not refresh:
        try:
            return pd.read_parquet(key)
        except Exception:  # noqa: BLE001
            pass
    import yfinance as yf
    print(f"시세 수집 {len(tickers)}종목 · {years}년 (캐시: {key.name})")
    frames = {}
    for t in tickers:
        try:
            h = yf.Ticker(t).history(period=f"{years}y", interval="1d", auto_adjust=True)
            c = h["Close"].dropna() if h is not None and not h.empty else None
            if c is not None and len(c) > 60:
                c.index = c.index.tz_localize(None).normalize()
                frames[t] = c
        except Exception as e:  # noqa: BLE001
            print(f"  건너뜀 {t}: {e}", file=sys.stderr)
    if not frames:
        raise SystemExit("시세를 하나도 받지 못했다 — 네트워크 확인")
    df = pd.DataFrame(frames).sort_index()
    try:
        df.to_parquet(key)
    except Exception:  # noqa: BLE001
        pass                                   # pyarrow 없으면 캐시만 생략
    return df


def snapshot(df: pd.DataFrame, i: int, meta: dict) -> dict:
    """i번째 거래일의 market.json 형태 — 전략이 보는 것은 이것뿐이다(미래 없음)."""
    inst = {}
    row = df.iloc[i]
    for t in df.columns:
        px = row.get(t)
        if pd.isna(px):
            continue
        name, cat = meta[t]
        d = {"name": name, "category": cat, "last": float(px),
             "data_date": df.index[i].strftime("%Y-%m-%d")}
        if i >= 20:
            base = df[t].iloc[i - 20]
            if not pd.isna(base) and base:
                d["chg_20d_pct"] = round((px / base - 1) * 100, 2)
        if i >= 5:
            base = df[t].iloc[i - 5]
            if not pd.isna(base) and base:
                d["chg_5d_pct"] = round((px / base - 1) * 100, 2)
        inst[t] = d
    return {"instruments": inst}


def run(sid: str, df: pd.DataFrame, meta: dict, start_i: int) -> dict:
    strat = get(sid)
    holdings: dict = {}
    cash = float(START_CAPITAL)
    applied: list[str] = []
    equity: list[tuple[str, float]] = []
    trades = 0

    # ⚠️ 마지막으로 알려진 가격을 **이월**한다. 어떤 날 특정 종목 시세가 비었다고
    #    그 보유분을 0원으로 평가하면, 자산곡선이 가짜로 폭락하고 MDD가 -100%로 찍힌다.
    last_px: dict[str, float] = {}

    def valuate() -> float:
        return cash + sum(q["qty"] * last_px.get(t, 0.0) for t, q in holdings.items())

    for i in range(start_i, len(df)):
        date = df.index[i].strftime("%Y-%m-%d")
        snap = snapshot(df, i, meta)
        last_px.update({t: d["last"] for t, d in snap["instruments"].items()})
        value = valuate()

        ctx = Context(date=date, session="kr", market=snap, history=[],
                      portfolio={"cash": cash, "holdings": holdings,
                                 "total_value": value, "applied_orders": applied})
        doc = strat.decide(ctx)

        for o in doc.get("orders", []):
            act, t = o.get("action"), o.get("ticker")
            if act not in ("buy", "sell") or t not in snap["instruments"]:
                continue
            d = snap["instruments"][t]
            info = {"name": d["name"], "category": d["category"], "currency": "KRW",
                    "data_date": d["data_date"]}
            px = d["last"]
            if act == "buy":
                cash, tr = exec_buy(holdings, cash, t, info, o.get("krw", 0), px, px,
                                    None, date, "kr", o.get("reason", ""), "백테스트",
                                    fractional=(d["category"] == "kr_index"))
            else:
                cash, tr = exec_sell(holdings, cash, t, info, o.get("qty"), px,
                                     date, "kr", o.get("reason", ""), "백테스트")
            if tr:
                trades += 1
        applied.append(f"{date}-kr")
        equity.append((date, valuate()))

    return {"equity": equity, "trades": trades}


def stats(equity: list[tuple[str, float]], bench: list[tuple[str, float]]) -> dict:
    if len(equity) < 2:
        return {}
    v = [x[1] for x in equity]
    ret = (v[-1] / v[0] - 1) * 100
    peak, mdd = v[0], 0.0
    for x in v:
        peak = max(peak, x)
        mdd = min(mdd, (x / peak - 1) * 100)
    b = [x[1] for x in bench]
    bret = (b[-1] / b[0] - 1) * 100 if len(b) >= 2 else 0.0
    yrs = max(len(v) / 252, 1e-9)
    return {"from": equity[0][0], "to": equity[-1][0], "days": len(v),
            "return_pct": round(ret, 2), "cagr_pct": round(((v[-1] / v[0]) ** (1 / yrs) - 1) * 100, 2),
            "bench_pct": round(bret, 2), "excess_pct": round(ret - bret, 2),
            "mdd_pct": round(mdd, 2)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("strategy")
    ap.add_argument("--years", type=int, default=3)
    ap.add_argument("--split", type=float, default=0.7, help="학습구간 비율 (나머지가 검증구간)")
    ap.add_argument("--refresh", action="store_true", help="시세 캐시 무시하고 다시 받기")
    a = ap.parse_args()

    meta = universe()
    if BENCH not in meta:
        meta[BENCH] = ("코스피", "kr_index")
    df = fetch(sorted(meta), a.years, a.refresh).dropna(how="all")
    df = df[[c for c in df.columns if c in meta]]
    if BENCH not in df.columns:
        raise SystemExit(f"벤치마크 {BENCH} 시세를 못 받았다")

    warm = 21                                     # chg_20d_pct 가 생기는 시점부터 시작
    cut = warm + int((len(df) - warm) * a.split)
    r = run(a.strategy, df, meta, warm)
    eq = r["equity"]
    bq = [(df.index[i].strftime("%Y-%m-%d"), float(df[BENCH].iloc[i])) for i in range(warm, len(df))]

    strat = get(a.strategy)
    print(f"\n📉 백테스트 — {strat.NAME}")
    print(f"   종목 {len(df.columns)}개 · {df.index[0]:%Y-%m-%d} ~ {df.index[-1]:%Y-%m-%d} "
          f"({len(df)}거래일) · 거래 {r['trades']}건\n")

    k = cut - warm
    parts = [("전체", eq, bq), ("학습구간(in-sample)", eq[:k], bq[:k]),
             ("검증구간(out-of-sample)", eq[k:], bq[k:])]
    print(f"   {'구간':24}{'기간':>7}{'전략':>9}{'코스피':>9}{'초과':>9}{'MDD':>9}")
    res = {}
    for label, e, b in parts:
        s = stats(e, b)
        if not s:
            continue
        res[label] = s
        print(f"   {label:24}{s['days']:>6}일{s['return_pct']:>+8.2f}%{s['bench_pct']:>+8.2f}%"
              f"{s['excess_pct']:>+8.2f}%p{s['mdd_pct']:>+8.2f}%")

    oos = res.get("검증구간(out-of-sample)")
    print()
    if oos:
        verdict = ("✅ 검증구간에서도 벤치마크를 이겼다" if oos["excess_pct"] > 0
                   else "❌ 검증구간에서 벤치마크에 졌다 — 이 규칙은 쓰지 않는다")
        print(f"   판정: {verdict} ({oos['excess_pct']:+.2f}%p)")
    print("   ⚠️ 판단은 **검증구간 숫자로만** 한다. 학습구간이 좋은 건 당연하다(곡선맞춤).")
    print("   ⚠️ 일봉 종가 체결 · 수수료/세금 없음 · 워치리스트 생존편향 있음.\n")

    out = REPO / ".backtest-cache" / f"result-{a.strategy}.json"
    out.write_text(json.dumps({"strategy": a.strategy, "years": a.years,
                               "split": a.split, "result": res, "trades": r["trades"]},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"   저장: {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
