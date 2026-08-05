"""
🤖 평균회귀 — **가장 많이 떨어진 것을 산다.** (`_ranked` 계열, sign=+1)

AI 4인이 2026-07-31에 한 판단의 **정반대**다. 그날 코스피 +17.91% 반등을 이끈 건
폭락의 진앙(SK하이닉스 +29.9%·삼성전자 +26.8%)이었는데, 4인 전원이 "낙하하는 칼은
안 잡는다"며 배제하고 방어주만 샀고 그 방어주가 정확히 반등 하위였다.

이 전략은 그 회피가 옳았는지를 판정하기 위해 존재한다.
쌍둥이 전략은 `momentum`(sign=-1) — 둘의 차이는 부호 하나뿐이다.
"""

from __future__ import annotations

from ._base import Context
from ._ranked import N, decide_ranked

ID = "meanrev"
NAME = f"평균회귀 (20일 낙폭 상위 {N} 동일비중)"


def decide(ctx: Context) -> dict:
    return decide_ranked(ID, ctx, sign=+1, label="낙폭")
