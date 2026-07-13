"""
매일 실행되는 시장 데이터 수집 스크립트 (확장판).

- config/watchlist.yaml 의 종목 목록을 읽어 yfinance로 1년치 시세를 받아온다.
- 각 종목에 대해 등락률·모멘텀·다중 이동평균·추세배열·RSI·MACD·볼린저 위치·
  52주 고저 위치·거래량 비율 등을 계산한다.
- 결과를 data/YYYY-MM-DD/market.json 에 저장하고, 상승/하락 상위 종목(movers)을 요약한다.

이 JSON을 Claude가 읽어서 뉴스(웹검색)와 함께 리포트를 작성한다.
(HTML 직접 크롤링은 자주 깨져서, 안정적인 시세 소스(yfinance)를 1차로 쓴다.)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

KST = timezone(timedelta(hours=9))
REPO = Path(__file__).resolve().parent.parent


def r(x, n=2):
    """반올림 헬퍼 (None/NaN 안전)."""
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
        return round(float(x), n)
    except (TypeError, ValueError):
        return None


def rsi14(close: pd.Series, period: int = 14):
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    val = (100 - 100 / (1 + rs)).iloc[-1]
    return r(val, 1)


def macd(close: pd.Series):
    """MACD(12,26,9). (macd, signal, hist) 마지막 값."""
    if len(close) < 35:
        return None, None, None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal
    return r(macd_line.iloc[-1], 3), r(signal.iloc[-1], 3), r(hist.iloc[-1], 3)


def bollinger_pct(close: pd.Series, period: int = 20):
    """20일 볼린저밴드 내 위치(0=하단, 1=상단). 범위 밖이면 <0 또는 >1."""
    if len(close) < period:
        return None
    ma = close.tail(period).mean()
    sd = close.tail(period).std()
    if sd == 0 or pd.isna(sd):
        return None
    upper, lower = ma + 2 * sd, ma - 2 * sd
    last = close.iloc[-1]
    return r((last - lower) / (upper - lower), 2)


def pct_change_ago(close: pd.Series, n: int):
    """n거래일 전 대비 등락률(%)."""
    if len(close) <= n:
        return None
    base = close.iloc[-1 - n]
    return r((close.iloc[-1] / base - 1) * 100, 2) if base else None


def trend_label(ma5, ma20, ma60):
    if None in (ma5, ma20, ma60):
        return None
    if ma5 > ma20 > ma60:
        return "상승배열"
    if ma5 < ma20 < ma60:
        return "하락배열"
    return "혼조"


def analyze(ticker: str, name: str, category: str) -> dict:
    hist = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)
    if hist is None or hist.empty or "Close" not in hist:
        raise ValueError("빈 데이터")

    close = hist["Close"].dropna()
    if len(close) < 2:
        raise ValueError("데이터 부족")

    last, prev = close.iloc[-1], close.iloc[-2]
    chg_pct = r((last / prev - 1) * 100) if prev else None

    ma5 = r(close.tail(5).mean()) if len(close) >= 5 else None
    ma20 = r(close.tail(20).mean()) if len(close) >= 20 else None
    ma60 = r(close.tail(60).mean()) if len(close) >= 60 else None
    ma120 = r(close.tail(120).mean()) if len(close) >= 120 else None

    w52_high, w52_low = r(close.max()), r(close.min())
    macd_line, macd_sig, macd_hist = macd(close)

    vol = vol_avg20 = vol_ratio = None
    if "Volume" in hist:
        v = hist["Volume"].dropna()
        if len(v) and float(v.iloc[-1]) > 0:
            vol = round(float(v.iloc[-1]))
            if len(v) >= 20:
                avg = float(v.tail(20).mean())
                vol_avg20 = round(avg)
                vol_ratio = r(vol / avg, 2) if avg else None

    return {
        "name": name,
        "category": category,
        "data_date": close.index[-1].strftime("%Y-%m-%d"),
        "last": r(last),
        "prev": r(prev),
        "chg_pct": chg_pct,
        "chg_5d_pct": pct_change_ago(close, 5),
        "chg_20d_pct": pct_change_ago(close, 20),
        "ma5": ma5,
        "ma20": ma20,
        "ma60": ma60,
        "ma120": ma120,
        "vs_ma20_pct": r((last / ma20 - 1) * 100) if ma20 else None,
        "vs_ma60_pct": r((last / ma60 - 1) * 100) if ma60 else None,
        "trend": trend_label(ma5, ma20, ma60),
        "rsi14": rsi14(close),
        "macd": macd_line,
        "macd_signal": macd_sig,
        "macd_hist": macd_hist,
        "bollinger_pct": bollinger_pct(close),
        "w52_high": w52_high,
        "w52_low": w52_low,
        "pct_from_52w_high": r((last / close.max() - 1) * 100) if close.max() else None,
        "pct_from_52w_low": r((last / close.min() - 1) * 100) if close.min() else None,
        "volume": vol,
        "vol_avg20": vol_avg20,
        "vol_ratio": vol_ratio,
    }


def load_watchlist() -> list[tuple[str, str, str]]:
    cfg_path = REPO / "config" / "watchlist.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    items: list[tuple[str, str, str]] = []
    for category, tickers in (data or {}).items():
        for ticker, name in (tickers or {}).items():
            items.append((str(ticker), str(name), str(category)))
    return items


def main() -> int:
    today = datetime.now(KST).strftime("%Y-%m-%d")
    out_dir = REPO / "data" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "market.json"

    watchlist = load_watchlist()
    print(f"수집 대상 {len(watchlist)}개 종목\n")

    instruments: dict[str, dict] = {}
    errors: dict[str, str] = {}

    for ticker, name, category in watchlist:
        try:
            d = analyze(ticker, name, category)
            instruments[ticker] = d
            chg = d["chg_pct"]
            print(f"  OK  {name:<14} {str(d['last']):>13}  ({chg:+}% )  RSI {d['rsi14']}  {d['trend'] or ''}")
        except Exception as e:  # noqa: BLE001
            errors[ticker] = str(e)
            print(f"  ERR {name:<14} {ticker}: {e}", file=sys.stderr)

    # 상승/하락 상위 (movers)
    ranked = sorted(
        ((t, d["name"], d["chg_pct"], d["category"]) for t, d in instruments.items() if d["chg_pct"] is not None),
        key=lambda x: x[2],
    )
    def fmt(rows):
        return [{"ticker": t, "name": n, "chg_pct": c, "category": cat} for t, n, c, cat in rows]
    movers = {
        "top_gainers": fmt(list(reversed(ranked[-5:]))),
        "top_losers": fmt(ranked[:5]),
    }

    result = {
        "as_of": today,
        "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "source": "yfinance",
        "count": len(instruments),
        "movers": movers,
        "instruments": instruments,
        "errors": errors,
    }

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {out_path}  (성공 {len(instruments)} / 실패 {len(errors)})")
    if movers["top_gainers"]:
        print("  상승 TOP:", ", ".join(f"{m['name']}({m['chg_pct']:+}%)" for m in movers["top_gainers"][:3]))
        print("  하락 TOP:", ", ".join(f"{m['name']}({m['chg_pct']:+}%)" for m in movers["top_losers"][:3]))
    return 0 if instruments else 1


if __name__ == "__main__":
    raise SystemExit(main())
