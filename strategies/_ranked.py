"""
순위 기반 전략의 공통 뼈대 — "20일 수익률로 줄 세워 위/아래 N개를 동일비중으로 보유".

`sign`만 뒤집으면 정반대 전략이 된다:
  · sign=+1 → **평균회귀**: 가장 많이 떨어진 N개를 산다 (진앙을 잡는다)
  · sign=-1 → **추세추종**: 가장 많이 오른 N개를 산다 (주도주를 따라간다)

둘을 같은 코드로 만든 이유는 **깨끗한 A/B**를 위해서다. 구현이 다르면
성과 차이가 규칙 때문인지 구현 차이 때문인지 알 수 없다. 여기선 부호 하나만 다르다.

2026-07-31 사건이 이 A/B의 출발점이다 — 코스피 +17.91% 반등을 이끈 건 폭락의 진앙
(SK하이닉스 +29.9%·삼성전자 +26.8%)이었고, AI 4인은 전원 그걸 배제했다.
"진앙을 사는 게 맞았나"를 서사가 아니라 몇 년치 숫자로 판정한다.
"""

from __future__ import annotations

from ._base import Context, buy, hold, orders, sell

N = 5              # 보유 종목 수 — 이 계열의 유일한 파라미터


def decide_ranked(sid: str, ctx: Context, sign: int, label: str) -> dict:
    if ctx.session != "kr":
        return orders(sid, ctx, [hold("미국장 세션 · 한국 전략")], "보유 유지")

    rows = [(t, d) for t, d in ctx.universe() if d.get("chg_20d_pct") is not None]
    if not rows:
        return orders(sid, ctx, [hold("지표 부족 · 대기")], "대기")
    # sign=+1이면 오름차순(가장 많이 빠진 것부터), -1이면 내림차순(가장 많이 오른 것부터)
    rows.sort(key=lambda x: sign * x[1]["chg_20d_pct"])
    targets = rows[:N]

    want = {t for t, _ in targets}
    held = {t for t, h in ctx.holdings.items() if float(h.get("qty", 0)) > 0}

    items: list[dict] = []
    # ① 목표에서 빠진 종목 전량 매도 — 현금이 먼저 풀려야 아래 매수가 체결된다
    #    (portfolio.py는 주문서에 적힌 순서대로 처리한다)
    freed = 0.0
    for t in sorted(held - want):
        h = ctx.holdings[t]
        px = ctx.price(t)
        if px is None:                       # 시세가 없으면 이번 회차엔 못 판다
            continue
        freed += float(h.get("qty", 0)) * px
        items.append(sell(t, h.get("name", t), f"{label} 상위 이탈 · 리밸런싱"))

    # ② 새로 편입할 종목에 현금을 동일비중으로 나눈다
    missing = [(t, d) for t, d in targets if t not in held]
    if missing:
        budget = (ctx.cash + freed) / len(missing)
        for t, d in missing:
            v = d["chg_20d_pct"]
            items.append(buy(t, d.get("name", t), budget, f"20일 {v:+.1f}% · {label} 상위 {N}"))

    if not items:
        return orders(sid, ctx, [hold("목표 포트폴리오 유지 · 거래 없음")], "유지")
    top = targets[0][1]
    return orders(sid, ctx, items, f"{label} 상위 {N} 리밸런싱 · 최대 {top['chg_20d_pct']:+.0f}%")
