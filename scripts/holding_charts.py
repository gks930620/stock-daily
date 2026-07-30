"""
보유 종목별 '일별 금액 그래프' 생성 — 포트폴리오 상세 페이지에서 종목을 펼쳤을 때 보이는 차트.

무엇을 그리나
  · 최근 3개월 일별 종가 선그래프 (해당 종목의 원통화 기준: 한국=원, 미국=달러)
  · 그 위에 **내 매수 시점**을 🔴 점 + 날짜로 표기 (lots 기준, 같은 날 여러 건은 합산)
  · 평균단가 점선 + 현재가 점선 → "지금 내가 이익인지 손실인지"가 한눈에 보인다

왜 별도 스크립트인가
  portfolio.py는 시세 스냅샷(market.json) 하나만 보는 순수 계산기라서 과거 시계열이 없다.
  네 계좌(성향)를 다 돌린 뒤 이 스크립트가 한 번만 실행되어,
  보유 종목의 합집합에 대해 yfinance를 **티커당 1회만** 호출한다(중복 제거).

실행:  python scripts/holding_charts.py          (portfolio.py 4회 뒤에)
출력:  assets/portfolio/h-<persona>-<slug>.png
       + _data/portfolio-<persona>.json 의 각 보유종목에 "chart" 파일명 주입
         (생성 성공한 것만 넣으므로, 페이지는 {% if h.chart %}로 안전하게 분기 가능)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as _fm
from matplotlib.ticker import FuncFormatter

for _f in ("Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic"):
    if _f in {f.name for f in _fm.fontManager.ttflist}:
        matplotlib.rcParams["font.family"] = _f
        break
matplotlib.rcParams["axes.unicode_minus"] = False

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "assets" / "portfolio"
PERIOD = "3mo"

UP = "#d63c2f"      # 한국식: 이익·상승 = 빨강
DOWN = "#2563d0"    # 손실·하락 = 파랑
LINE = "#334155"
BUY = "#d63c2f"


def slug(ticker: str) -> str:
    """005930.KS → 005930-ks · ^GSPC → gspc · GC=F → gc-f (파일명 안전)"""
    return re.sub(r"[^a-z0-9]+", "-", ticker.lower()).strip("-")


def fetch(ticker: str):
    """일별 종가 시계열. 실패하면 None (차트 없이 넘어간다)."""
    try:
        import yfinance as yf
        h = yf.Ticker(ticker).history(period=PERIOD, interval="1d", auto_adjust=True)
        if h is None or h.empty or "Close" not in h:
            return None
        c = h["Close"].dropna()
        return c if len(c) >= 5 else None
    except Exception as e:  # noqa: BLE001
        print(f"  시세 조회 실패 {ticker}: {e}", file=sys.stderr)
        return None


def draw(close, hv: dict, persona: str) -> str | None:
    """종목 1개 차트를 그려 파일명 반환. 실패 시 None."""
    ticker = hv["ticker"]
    is_usd = hv.get("currency") == "USD"
    unit = hv.get("unit", "주")

    # 매수 시점(lots) — 같은 날짜는 수량 합산, 가격은 수량가중평균
    by_date: dict[str, dict] = {}
    for lot in hv.get("lots", []):
        d = lot.get("date")
        px = lot.get("price_native") if is_usd else lot.get("price_krw")
        if not d or px is None:
            continue
        q = float(lot.get("qty") or 0)
        agg = by_date.setdefault(d, {"qty": 0.0, "pv": 0.0})
        agg["qty"] += q
        agg["pv"] += px * q
    buys = []
    for d, agg in sorted(by_date.items()):
        if agg["qty"] <= 0:
            continue
        buys.append((d, agg["pv"] / agg["qty"], agg["qty"]))

    avg = None
    if is_usd:
        s = (hv.get("avg_native_str") or "").replace("$", "").replace(",", "")
        try:
            avg = float(s) if s else None
        except ValueError:
            avg = None
    else:
        avg = hv.get("avg_krw")
    cur = hv["price_native"] if is_usd and hv.get("price_native") is not None else None
    if cur is None:
        cur = float(str(hv.get("price_str", "0")).replace(",", "")) if not is_usd else None
    if cur is None:
        cur = float(close.iloc[-1])

    dates = [d.strftime("%Y-%m-%d") for d in close.index]
    vals = [float(v) for v in close.values]
    profit = avg is not None and cur >= avg
    accent = UP if profit else DOWN

    fig, ax = plt.subplots(figsize=(8.6, 3.1))
    ax.plot(range(len(vals)), vals, color=LINE, linewidth=1.7, zorder=3)
    ax.fill_between(range(len(vals)), min(vals), vals, color=accent, alpha=0.07, zorder=1)

    if avg:
        ax.axhline(avg, color="#94a3b8", linestyle="--", linewidth=1.1, zorder=2)
        ax.annotate(f"평단 {avg:,.2f}" if is_usd else f"평단 {avg:,.0f}",
                    xy=(0, avg), xytext=(3, 4), textcoords="offset points",
                    fontsize=9, color="#64748b", fontweight="bold")
    ax.axhline(cur, color=accent, linestyle=":", linewidth=1.2, zorder=2)

    # 🔴 매수 시점 — 차트 x축(거래일) 위 가장 가까운 위치에 찍는다
    idx = {d: i for i, d in enumerate(dates)}
    placed = 0
    for d, px, q in buys:
        i = idx.get(d)
        if i is None:                       # 매수일이 이 구간(3개월) 밖이면 첫 지점으로 당겨 표시
            later = [j for dd, j in idx.items() if dd >= d]
            if not later:
                continue
            i = min(later)
        ax.scatter([i], [px], s=74, color=BUY, edgecolor="white", linewidth=1.6, zorder=5)
        ax.annotate(f"매수 {q:g}{unit}\n{d[5:]}", xy=(i, px), xytext=(0, -30),
                    textcoords="offset points", ha="center", fontsize=8.4,
                    color=BUY, fontweight="bold", zorder=6)
        placed += 1

    pl = f"{(cur/avg - 1) * 100:+.2f}%" if avg else ""
    ax.set_title(f"{hv['name']}  ·  최근 3개월  ·  현재 {cur:,.2f}{'$' if is_usd else '원'}  {pl}"
                 if is_usd else
                 f"{hv['name']}  ·  최근 3개월  ·  현재 {cur:,.0f}원  {pl}",
                 fontsize=11.5, fontweight="bold", color="#1e293b", loc="left")

    ax.yaxis.set_major_formatter(FuncFormatter(
        lambda v, _: f"${v:,.0f}" if is_usd else (f"{v/10000:.0f}만" if v >= 10000 else f"{v:,.0f}")))
    step = max(1, len(dates) // 6)
    ax.set_xticks(range(0, len(dates), step))
    ax.set_xticklabels([dates[i][5:] for i in range(0, len(dates), step)], fontsize=9)
    ax.tick_params(axis="y", labelsize=9)
    ax.grid(alpha=0.18)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.margins(y=0.16)
    fig.tight_layout()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"h-{persona}-{slug(ticker)}.png"
    fig.savefig(OUT_DIR / fname, dpi=108)
    plt.close(fig)
    print(f"  {persona:11} {hv['name']:<16} 매수표기 {placed}건 → {fname}")
    return fname


def main() -> int:
    states = sorted((REPO / "_data").glob("portfolio-*.json"))
    if not states:
        print("_data/portfolio-*.json 없음 — 건너뜀", file=sys.stderr)
        return 0

    # 1) 보유 티커 합집합 → 티커당 1회만 시세 조회
    loaded = []
    tickers: set[str] = set()
    for sp in states:
        st = json.loads(sp.read_text(encoding="utf-8"))
        loaded.append((sp, st))
        for hv in st.get("holdings_view", []):
            tickers.add(hv["ticker"])
    if not tickers:
        print("보유 종목 없음 — 차트 생성 생략")
        return 0
    print(f"보유 티커 {len(tickers)}개 시세 조회 ({PERIOD})")
    series = {t: fetch(t) for t in sorted(tickers)}
    ok = sum(1 for v in series.values() if v is not None)
    print(f"  조회 성공 {ok}/{len(tickers)}\n종목별 차트 생성:")

    # 2) 계좌별로 차트 생성 + JSON에 chart 파일명 주입
    made = 0
    for sp, st in loaded:
        persona = st.get("persona") or sp.stem.replace("portfolio-", "")
        changed = False
        for hv in st.get("holdings_view", []):
            close = series.get(hv["ticker"])
            if close is None:
                hv.pop("chart", None)
                continue
            try:
                fname = draw(close, hv, persona)
            except Exception as e:  # noqa: BLE001
                print(f"  차트 실패 {persona}/{hv['ticker']}: {e}", file=sys.stderr)
                fname = None
            if fname:
                hv["chart"] = fname
                changed = True
                made += 1
            else:
                hv.pop("chart", None)
        # by_market은 소계만 담고 보유목록을 중복 저장하지 않으므로 여기서 동기화할 것이 없다.
        _ = changed
        sp.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n차트 {made}개 생성 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
