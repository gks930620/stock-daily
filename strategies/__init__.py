"""
전략 레지스트리 — id → 전략 모듈.

새 전략 추가 절차
  1. `strategies/<id>.py` 에 `ID` · `NAME` · `decide(ctx) -> dict` 를 만든다
  2. 아래 REGISTRY 에 등록한다
  3. `python scripts/backtest.py <id>` 로 **검증구간 성과를 먼저 확인**한다
  4. 계좌로 굴리려면 `scripts/portfolio.py` 의 PERSONAS 에 항목을 추가한다

⚠️ 3번을 건너뛰지 말 것. 검증 없이 계좌부터 만들면 "잘하는지 모르는 계좌"가
   하나 더 늘 뿐이다 — 그게 정확히 이 프로젝트가 겪던 문제였다 (docs/RULES.md §0-2).
"""

from __future__ import annotations

from . import benchmark, meanrev, momentum

REGISTRY = {
    benchmark.ID: benchmark,
    meanrev.ID: meanrev,       # 낙폭 상위 매수 (진앙을 잡는다)
    momentum.ID: momentum,     # 상승 상위 매수 (주도주를 따라간다) — meanrev와 부호만 다른 쌍둥이
}


def get(strategy_id: str):
    if strategy_id not in REGISTRY:
        raise SystemExit(f"알 수 없는 전략: {strategy_id} — {sorted(REGISTRY)}")
    return REGISTRY[strategy_id]
