"""
📊 벤치마크 — 코스피를 사서 그냥 들고 있는다. **판단을 일절 하지 않는 기준선.**

왜 이 계좌가 필요한가
  "AI 4인이 다 손해"처럼 보여도, 시장이 그보다 더 빠졌으면 실제로는 이긴 것이다.
  비교 대상이 없으면 잘한 건지 못한 건지 **말할 수가 없다.** 이 계좌가 그 눈금이다.
  가장 이기기 어려운 상대이기도 하다 — 아무 것도 안 하고 수수료도 안 내니까.

규칙 (파라미터 0개 — 곡선맞춤이 원천적으로 불가능하다)
  · 첫 회차에 현금 전액으로 코스피(^KS11) 매수
  · 그 뒤로는 영원히 아무것도 하지 않는다

⚠️ 이상화된 벤치마크다: 지수를 직접 산 것으로 계산하므로 ETF 보수·추적오차·
   호가 스프레드가 없다. 실제로는 KODEX200 같은 ETF를 사야 하고 그만큼 조금 불리하다.
   즉 이 기준선은 **현실보다 약간 세다** — 이걸 이기면 진짜 이긴 것이다.
"""

from __future__ import annotations

from ._base import Context, buy, hold, orders

ID = "bench"
NAME = "벤치마크 (코스피 매수 후 보유)"
INDEX = "^KS11"


def decide(ctx: Context) -> dict:
    # 한국장 세션에서만 움직인다 (코스피니까)
    if ctx.session != "kr":
        return orders(ID, ctx, [hold("미국장 세션 · 해당 없음")], "보유 유지")

    if ctx.qty(INDEX) > 0:
        # 이미 샀다. 이 전략의 전부다 — 아무것도 하지 않는다.
        return orders(ID, ctx, [hold("매수 후 보유 · 거래 없음")], "보유 유지")

    px = ctx.price(INDEX)
    if not px or ctx.cash <= 0:
        return orders(ID, ctx, [hold("시세 없음 또는 현금 없음")], "대기")

    name = (ctx.inst(INDEX) or {}).get("name", "코스피")
    return orders(ID, ctx, [buy(INDEX, name, ctx.cash, "전액 매수 후 보유")],
                  "코스피 전액 매수 · 이후 무거래")
