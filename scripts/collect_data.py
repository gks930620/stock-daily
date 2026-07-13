"""
매일 실행되는 시장 데이터 수집 스크립트.

- yfinance로 미국·한국 지수 / 환율 / VIX / 금리 / 관심종목의 시세를 받아온다.
- 각 종목에 대해 등락률, 이동평균(5·20), RSI(14), 52주 고저 대비 위치, 거래량 등을 계산한다.
- 결과를 data/YYYY-MM-DD/market.json 에 저장하고 요약을 출력한다.

이 JSON을 Claude가 읽어서 뉴스(웹검색)와 함께 리포트를 작성한다.
(HTML 직접 크롤링은 자주 깨져서, 안정적인 시세 소스(yfinance)를 1차로 쓴다.
 특정 사이트 크롤러가 필요하면 scripts/에 별도로 추가 확장.)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

# 한국 시간(KST)
KST = timezone(timedelta(hours=9))

# 수집 대상: (티커, 표시이름, 분류)
INSTRUMENTS = [
    # 미국 지수
    ("^GSPC", "S&P500", "us_index"),
    ("^IXIC", "나스닥종합", "us_index"),
    ("^DJI", "다우", "us_index"),
    # 리스크 지표
    ("^VIX", "VIX 변동성", "risk"),
    ("^TNX", "미 10년물 금리", "risk"),
    ("DX-Y.NYB", "달러인덱스", "risk"),
    # 한국 지수
    ("^KS11", "코스피", "kr_index"),
    ("^KQ11", "코스닥", "kr_index"),
    # 환율
    ("KRW=X", "원/달러", "fx"),
    # 관심 종목
    ("005930.KS", "삼성전자", "kr_stock"),
    ("000660.KS", "SK하이닉스", "kr_stock"),
    ("NVDA", "엔비디아", "us_stock"),
    ("TSLA", "테슬라", "us_stock"),
    ("AAPL", "애플", "us_stock"),
]


def rsi14(closes: pd.Series, period: int = 14) -> float | None:
    """Wilder RSI(14). 마지막 값 반환."""
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    val = (100 - 100 / (1 + rs)).iloc[-1]
    return None if pd.isna(val) else round(float(val), 1)


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


def analyze(ticker: str, name: str, category: str) -> dict:
    """한 종목의 1년치 시세를 받아 지표를 계산."""
    hist = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=True)
    if hist is None or hist.empty or "Close" not in hist:
        raise ValueError("빈 데이터")

    close = hist["Close"].dropna()
    if len(close) < 2:
        raise ValueError("데이터 부족")

    last = close.iloc[-1]
    prev = close.iloc[-2]
    chg_pct = (last / prev - 1) * 100 if prev else None

    ma5 = close.tail(5).mean() if len(close) >= 5 else None
    ma20 = close.tail(20).mean() if len(close) >= 20 else None

    w52_high = close.max()
    w52_low = close.min()
    pct_from_high = (last / w52_high - 1) * 100 if w52_high else None

    vol = None
    vol_avg20 = None
    if "Volume" in hist:
        v = hist["Volume"].dropna()
        if len(v):
            vol = float(v.iloc[-1])
            if len(v) >= 20:
                vol_avg20 = float(v.tail(20).mean())

    return {
        "name": name,
        "category": category,
        "data_date": close.index[-1].strftime("%Y-%m-%d"),
        "last": r(last),
        "prev": r(prev),
        "chg_pct": r(chg_pct),
        "ma5": r(ma5),
        "ma20": r(ma20),
        "rsi14": rsi14(close),
        "w52_high": r(w52_high),
        "w52_low": r(w52_low),
        "pct_from_52w_high": r(pct_from_high),
        "volume": vol,
        "vol_avg20": vol_avg20,
    }


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    today = datetime.now(KST).strftime("%Y-%m-%d")
    out_dir = repo / "data" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "market.json"

    instruments: dict[str, dict] = {}
    errors: dict[str, str] = {}

    for ticker, name, category in INSTRUMENTS:
        try:
            instruments[ticker] = analyze(ticker, name, category)
            d = instruments[ticker]
            print(f"  OK  {name:<10} {d['last']:>12}  ({d['chg_pct']:+}% )  RSI {d['rsi14']}")
        except Exception as e:  # noqa: BLE001 - 개별 실패가 전체를 막지 않게
            errors[ticker] = str(e)
            print(f"  ERR {name:<10} {ticker}: {e}", file=sys.stderr)

    result = {
        "as_of": today,
        "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "source": "yfinance",
        "count": len(instruments),
        "instruments": instruments,
        "errors": errors,
    }

    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {out_path}  (성공 {len(instruments)}개 / 실패 {len(errors)}개)")
    # 하나도 못 받으면 실패로 종료
    return 0 if instruments else 1


if __name__ == "__main__":
    raise SystemExit(main())
