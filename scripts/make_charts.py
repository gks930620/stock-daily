"""
주요 지수·종목의 차트 이미지(PNG)를 생성한다.

- 각 종목: 상단=종가+이동평균(20·60), 하단=RSI(14). 최근 6개월.
- 저장: assets/charts/YYYY-MM-DD/<slug>.png  (git에 커밋되어 사이트에 표시됨)
- 리포트에 삽입하고, Claude가 이 이미지를 직접 보고 시각 패턴을 분석에 반영한다.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 화면 없이 파일로 저장
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf

# 한글 폰트 (윈도우 기본). 없으면 무시.
try:
    matplotlib.rcParams["font.family"] = "Malgun Gothic"
except Exception:
    pass
matplotlib.rcParams["axes.unicode_minus"] = False

KST = timezone(timedelta(hours=9))
REPO = Path(__file__).resolve().parent.parent

# 차트로 그릴 종목 (티커, 표시이름)
CHART_TICKERS = [
    ("^KS11", "코스피"),
    ("^KQ11", "코스닥"),
    ("^GSPC", "S&P500"),
    ("^IXIC", "나스닥종합"),
    ("000660.KS", "SK하이닉스"),
    ("005930.KS", "삼성전자"),
    ("NVDA", "엔비디아"),
]


def slug(ticker: str) -> str:
    return ticker.replace("^", "").replace("=", "").replace(".", "_").replace("-", "_")


def rsi14(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    al = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return 100 - 100 / (1 + ag / al)


def make_chart(ticker: str, name: str, out_dir: Path) -> str | None:
    hist = yf.Ticker(ticker).history(period="6mo", interval="1d", auto_adjust=True)
    if hist is None or hist.empty:
        raise ValueError("빈 데이터")
    close = hist["Close"].dropna()
    if len(close) < 30:
        raise ValueError("데이터 부족")

    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    rsi = rsi14(close)
    last = close.iloc[-1]
    chg = (last / close.iloc[-2] - 1) * 100

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 6.2), sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )
    # 상단: 가격 + 이동평균
    ax1.plot(close.index, close, color="#1f77b4", linewidth=1.6, label="종가")
    ax1.plot(ma20.index, ma20, color="#ff7f0e", linewidth=1.0, label="20일선")
    ax1.plot(ma60.index, ma60, color="#2ca02c", linewidth=1.0, label="60일선")
    ax1.set_title(f"{name} ({ticker})   최근가 {last:,.2f}  ({chg:+.2f}%)", fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(alpha=0.25)

    # 하단: RSI
    ax2.plot(rsi.index, rsi, color="#9467bd", linewidth=1.2)
    ax2.axhline(70, color="red", linestyle="--", linewidth=0.8, alpha=0.6)
    ax2.axhline(30, color="blue", linestyle="--", linewidth=0.8, alpha=0.6)
    ax2.set_ylim(0, 100)
    ax2.set_ylabel("RSI", fontsize=9)
    ax2.grid(alpha=0.25)

    fig.tight_layout()
    out_path = out_dir / f"{slug(ticker)}.png"
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return out_path.name


def main() -> int:
    today = datetime.now(KST).strftime("%Y-%m-%d")
    out_dir = REPO / "assets" / "charts" / today
    out_dir.mkdir(parents=True, exist_ok=True)

    made, errors = [], {}
    for ticker, name in CHART_TICKERS:
        try:
            fn = make_chart(ticker, name, out_dir)
            made.append((ticker, name, fn))
            print(f"  OK  {name:<12} → {fn}")
        except Exception as e:  # noqa: BLE001
            errors[ticker] = str(e)
            print(f"  ERR {name:<12} {ticker}: {e}", file=sys.stderr)

    print(f"\n생성 {len(made)}개 → {out_dir}  (실패 {len(errors)})")
    print(f"  리포트 삽입 경로 예: /stock-daily/assets/charts/{today}/{slug(CHART_TICKERS[0][0])}.png")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
