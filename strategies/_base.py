"""
알고리즘 전략의 공통 계약 (인터페이스).

핵심 설계 — **전략은 순수 함수다.**

    decide(ctx: Context) -> dict     # 주문서 JSON (AI 매니저가 내는 것과 같은 스키마)

`ctx`에는 **그 시점까지의 데이터만** 담긴다. 그래서 같은 함수를
  · 오늘 날짜로 부르면  → 라이브 매매 (scripts/run_strategy.py)
  · 과거 날짜로 돌리면  → 백테스트   (scripts/backtest.py)
둘 다 얻는다. "봇 따로, 백테스트 따로"를 만들지 않기 위한 규칙이다.

⚠️ 전략 안에서 절대 하면 안 되는 것 (하면 백테스트가 거짓말을 한다)
  · `datetime.now()` / 오늘 날짜 직접 조회      → `ctx.date`를 쓴다
  · yfinance·웹검색 등 외부 조회                → `ctx.market` / `ctx.history`만 본다
  · 미래 데이터 접근                            → Context가 애초에 과거만 담아 넘긴다

⚠️ 그리고 **파라미터는 적을수록 좋다.** 규칙에 손잡이가 많을수록 과거에만 맞는
   곡선맞춤(overfitting)이 된다. 새 파라미터를 넣을 땐 왜 필요한지 주석으로 남긴다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 세션별로 그 전략이 건드릴 수 있는 시장 (지금 열려 있는 시장만)
SESSION_CATS = {"kr": {"kr_stock"}, "us": {"us_stock", "us_sector"}}


@dataclass(frozen=True)
class Context:
    """전략이 볼 수 있는 세상 전부. 이 시점 '이후' 정보는 들어 있지 않다."""

    date: str                    # 회차 기준일 'YYYY-MM-DD'
    session: str                 # 'kr' | 'us'
    market: dict                 # 이 회차의 market.json (지금 보이는 시세·지표)
    history: list[dict] = field(default_factory=list)
    #   과거 회차들의 스냅샷 — 날짜 오름차순, **ctx.date 이전만**.
    #   각 원소는 {"date": "YYYY-MM-DD", "instruments": {...}}.
    portfolio: dict = field(default_factory=dict)   # 계좌 상태 (_data/portfolio-<id>.json)

    # ── 조회 헬퍼 ──────────────────────────────────────────────
    @property
    def instruments(self) -> dict:
        return self.market.get("instruments", {})

    def inst(self, ticker: str) -> dict | None:
        return self.instruments.get(ticker)

    def price(self, ticker: str) -> float | None:
        d = self.inst(ticker)
        return float(d["last"]) if d and d.get("last") is not None else None

    def universe(self, categories: set[str] | None = None) -> list[tuple[str, dict]]:
        """이번 세션에 **거래 가능한** 종목만. 시세 없는 종목은 뺀다."""
        cats = categories if categories is not None else SESSION_CATS.get(self.session, set())
        return [(t, d) for t, d in self.instruments.items()
                if d.get("category") in cats and d.get("last") is not None]

    def series(self, ticker: str, field_name: str = "last") -> list[tuple[str, float]]:
        """과거 회차들의 (날짜, 값) — 이 회차 값이 마지막. 미래는 없다."""
        out = []
        for snap in self.history:
            d = snap.get("instruments", {}).get(ticker)
            if d and d.get(field_name) is not None:
                out.append((snap["date"], float(d[field_name])))
        cur = self.inst(ticker)
        if cur and cur.get(field_name) is not None:
            out.append((self.date, float(cur[field_name])))
        return out

    @property
    def cash(self) -> float:
        return float(self.portfolio.get("cash", 0))

    @property
    def total_value(self) -> float:
        return float(self.portfolio.get("total_value") or self.cash)

    @property
    def holdings(self) -> dict:
        return self.portfolio.get("holdings", {}) or {}

    def qty(self, ticker: str) -> float:
        h = self.holdings.get(ticker)
        return float(h["qty"]) if h else 0.0

    @property
    def is_first_run(self) -> bool:
        return not self.holdings and not self.portfolio.get("applied_orders")


# ── 주문서 조립 (AI 매니저와 동일 스키마여야 체결기가 그대로 처리한다) ──
def orders(strategy_id: str, ctx: Context, items: list[dict], comment: str) -> dict:
    return {
        "date": ctx.date, "session": ctx.session,
        "persona": ctx.portfolio.get("persona") or strategy_id,
        "strategy": strategy_id,
        "comment": comment[:35],          # 매매일지 단답형 규칙 (RULES §3)
        "orders": items,
    }


def buy(ticker: str, name: str, krw: float, reason: str) -> dict:
    return {"action": "buy", "ticker": ticker, "name": name,
            "krw": round(krw), "reason": reason[:30]}


def sell(ticker: str, name: str, reason: str, qty: float | None = None) -> dict:
    o = {"action": "sell", "ticker": ticker, "name": name, "reason": reason[:30]}
    if qty is not None:
        o["qty"] = qty
    return o


def hold(reason: str) -> dict:
    return {"action": "hold", "reason": reason[:30]}
