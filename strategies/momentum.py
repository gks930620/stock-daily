"""
🤖 추세추종 — **가장 많이 오른 것을 산다.** (`_ranked` 계열, sign=-1)

`meanrev`의 쌍둥이이자 정반대. 구현은 같은 코드를 쓰고 **부호 하나만** 다르다.
그래서 성과 차이가 나면 그건 구현 차이가 아니라 **규칙 차이**다.
"""

from __future__ import annotations

from ._base import Context
from ._ranked import N, decide_ranked

ID = "momentum"
NAME = f"추세추종 (20일 상승 상위 {N} 동일비중)"


def decide(ctx: Context) -> dict:
    return decide_ranked(ID, ctx, sign=-1, label="상승")
