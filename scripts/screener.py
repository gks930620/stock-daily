"""
"오늘 오를 것 같은 비인기 종목" 후보 스크리너 (한국 시장).

⚠️ 확정 신호가 아니라 '후보 발굴'이다. 소형·중형주는 변동성·유동성 리스크가 크다.
   Claude가 이 후보들의 뉴스/재료를 웹검색으로 확인해 소수만 선별하고, 리스크를 함께 명시한다.

방식(2단계):
  1) FinanceDataReader로 KOSPI+KOSDAQ 전체 스냅샷을 받아,
     소형~중형(비인기) + 유동성 + 오늘 반등(양봉) 종목으로 1차 압축.
  2) 압축된 후보의 최근 시세를 받아 RSI·거래량급증·낙폭과대반등·저점권반등 신호 계산 후 상위 선별.
결과: data/YYYY-MM-DD/screener.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import FinanceDataReader as fdr

KST = timezone(timedelta(hours=9))
REPO = Path(__file__).resolve().parent.parent

# 1차 스냅샷 필터 파라미터
MARCAP_MIN = 1e11    # 시총 하한 1000억 (초소형 제외)
MARCAP_MAX = 5e12    # 시총 상한 5조   (대형주 제외 → '비인기')
AMOUNT_MIN = 3e9     # 거래대금 하한 30억 (유동성 확보)
CHG_MIN = 1.0        # 오늘 등락률 하한 (%)
SHORTLIST = 40       # 상세분석할 최대 종목 수
TOP_N = 15           # 최종 후보 수


def rsi14(close: pd.Series, period: int = 14):
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    ag = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    al = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = ag / al
    v = (100 - 100 / (1 + rs)).iloc[-1]
    return None if pd.isna(v) else round(float(v), 1)


def get_universe() -> pd.DataFrame:
    frames = []
    for mkt in ("KOSPI", "KOSDAQ"):
        try:
            df = fdr.StockListing(mkt)
            df["Market"] = mkt
            frames.append(df)
        except Exception as e:  # noqa: BLE001
            print(f"  [{mkt}] 목록 수집 실패: {e}", file=sys.stderr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main() -> int:
    today = datetime.now(KST).strftime("%Y-%m-%d")
    out_dir = REPO / "data" / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "screener.json"

    uni = get_universe()
    if uni.empty:
        out_path.write_text(
            json.dumps({"as_of": today, "error": "유니버스 수집 실패", "candidates": []},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print("유니버스 수집 실패 — 빈 screener.json 기록")
        return 1

    for col in ("ChagesRatio", "Marcap", "Amount", "Volume", "Close", "Open"):
        if col in uni:
            uni[col] = pd.to_numeric(uni[col], errors="coerce")

    # 1차 스냅샷 필터: 비인기(소형~중형) + 유동성 + 오늘 반등(양봉)
    f = uni[
        uni["Marcap"].between(MARCAP_MIN, MARCAP_MAX)
        & (uni["Amount"] >= AMOUNT_MIN)
        & (uni["ChagesRatio"] >= CHG_MIN)
        & (uni["Close"] >= uni["Open"])
    ].copy()
    f = f.sort_values("ChagesRatio", ascending=False).head(SHORTLIST)
    print(f"유니버스 {len(uni)}개 → 1차 통과 {len(f)}개 → 상세분석...")

    # 2차 상세: 최근 시세로 신호 계산
    start = (datetime.now(KST) - timedelta(days=90)).strftime("%Y-%m-%d")
    cands = []
    for _, row in f.iterrows():
        code = str(row["Code"]).zfill(6)
        name = str(row["Name"])
        try:
            h = fdr.DataReader(code, start)
            close = h["Close"].dropna()
            vol = h["Volume"].dropna()
            if len(close) < 25:
                continue
            last = float(close.iloc[-1])
            chg = (last / float(close.iloc[-2]) - 1) * 100
            chg20 = (last / float(close.iloc[-21]) - 1) * 100 if len(close) > 21 else None
            rsi = rsi14(close)
            vavg20 = float(vol.tail(20).mean()) if len(vol) >= 20 else None
            vratio = (float(vol.iloc[-1]) / vavg20) if vavg20 else None
            low40 = float(close.tail(40).min())
            near_low = (last / low40 - 1) * 100 if low40 else None

            signals = []
            if vratio is not None and vratio >= 2.5:
                signals.append("거래량급증")
            if rsi is not None and rsi < 40 and chg > 0:
                signals.append("과매도반등")
            if chg20 is not None and chg20 < -10 and chg > 0:
                signals.append("낙폭과대반등")
            if near_low is not None and near_low <= 8 and chg > 0:
                signals.append("저점권반등")
            if not signals:
                continue

            cands.append({
                "code": code,
                "name": name,
                "market": str(row.get("Market", "")),
                "marcap_억원": round(float(row["Marcap"]) / 1e8),
                "last": round(last),
                "chg_pct": round(chg, 2),
                "chg_20d_pct": round(chg20, 2) if chg20 is not None else None,
                "rsi14": rsi,
                "vol_ratio": round(vratio, 2) if vratio is not None else None,
                "near_40d_low_pct": round(near_low, 2) if near_low is not None else None,
                "signals": signals,
            })
        except Exception as e:  # noqa: BLE001
            print(f"  [{name}({code})] 상세 실패: {e}", file=sys.stderr)

    # 신호 수 → 거래량비율 순으로 랭킹
    cands.sort(key=lambda c: (len(c["signals"]), c["vol_ratio"] or 0), reverse=True)
    cands = cands[:TOP_N]

    result = {
        "as_of": today,
        "generated_at_kst": datetime.now(KST).isoformat(timespec="seconds"),
        "source": "FinanceDataReader",
        "universe_count": int(len(uni)),
        "shortlist_count": int(len(f)),
        "candidate_count": len(cands),
        "note": "확정 신호 아님. 소형주 변동성·유동성 리스크 큼. 뉴스/재료 확인 후 소수만 선별할 것.",
        "candidates": cands,
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {out_path}  (후보 {len(cands)}개)")
    for c in cands[:8]:
        print(f"  {c['name']:<12} {c['chg_pct']:+}%  RSI {c['rsi14']}  거래량x{c['vol_ratio']}  {c['signals']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
