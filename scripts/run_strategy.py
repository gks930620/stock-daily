"""
알고리즘 전략을 **라이브로** 실행해 주문서를 만든다 (AI 매니저의 알고리즘 판).

  python scripts/run_strategy.py <전략id> <kr|us> [계좌id]

AI 매니저와 완전히 같은 자리에 선다:
  · 같은 `data/<날짜>/market.json`을 본다
  · 같은 스키마의 `portfolio/orders/<날짜>-<세션>-<계좌id>.json`을 낸다
  · 체결·평가·페이지는 기존 `scripts/portfolio.py`가 그대로 처리한다
그래서 채점판(`scoreboard.py`)에서 4인과 **직접 비교**된다.

전략 함수는 순수 함수다 — 이 스크립트는 `Context`를 조립해 넘기는 일만 한다.
같은 함수를 과거 날짜로 돌리는 것이 `scripts/backtest.py`다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))          # strategies 패키지를 저장소 루트에서 import

from _rundate import run_date                     # noqa: E402
from portfolio import START_CAPITAL               # noqa: E402
from strategies import get                        # noqa: E402
from strategies._base import Context              # noqa: E402

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def load(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return default


def past_snapshots(today: str) -> list[dict]:
    """오늘 **이전** 회차 스냅샷만. 미래를 넘기면 백테스트가 거짓말을 한다."""
    out = []
    for f in sorted((REPO / "data").glob("*/market.json")):
        d = f.parent.name
        if d >= today:
            continue
        m = load(f)
        if m and m.get("instruments"):
            out.append({"date": d, "instruments": m["instruments"]})
    return out


def main() -> int:
    if len(sys.argv) < 3:
        print("사용법: run_strategy.py <전략id> <kr|us> [계좌id]", file=sys.stderr)
        return 2
    sid, session = sys.argv[1], sys.argv[2]
    account = sys.argv[3] if len(sys.argv) > 3 else sid
    if session not in ("kr", "us"):
        print(f"세션은 kr|us — 받은 값: {session!r}", file=sys.stderr)
        return 2

    strat = get(sid)
    today = run_date()
    market = load(REPO / "data" / today / "market.json")
    if not market:
        print(f"[{account}] data/{today}/market.json 없음 — 주문서 생성 불가", file=sys.stderr)
        return 1

    # 계좌 파일이 아직 없으면 **현금 1억으로 개설된 상태**로 본다.
    #   ⚠️ 이걸 빠뜨리면 첫 회차에 cash=0으로 보여 전략이 아무것도 못 사고,
    #      매수가 하루 밀려 진입가가 달라진다(벤치마크 백필에서 실제로 겪음).
    state = load(REPO / "_data" / f"portfolio-{account}.json", None)
    if not state:
        state = {"cash": START_CAPITAL, "holdings": {}, "applied_orders": [],
                 "total_value": START_CAPITAL, "persona": account}

    ctx = Context(
        date=today, session=session, market=market,
        history=past_snapshots(today), portfolio=state,
    )
    doc = strat.decide(ctx)
    doc["persona"] = account                      # 계좌 id로 덮어쓴다 (체결기가 이걸 본다)

    out = REPO / "portfolio" / "orders" / f"{today}-{session}-{account}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    acts = [o for o in doc.get("orders", []) if o.get("action") in ("buy", "sell")]
    print(f"[{account}] {strat.NAME}")
    print(f"  {today} {session} · 주문 {len(acts)}건 · {doc.get('comment','')}")
    for o in doc.get("orders", []):
        tag = {"buy": "매수", "sell": "매도"}.get(o.get("action"), "유지")
        krw = f" {o['krw']:,}원" if o.get("krw") else ""
        print(f"    {tag} {o.get('name','-')}{krw} — {o.get('reason','')}")
    print(f"  → {out.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
