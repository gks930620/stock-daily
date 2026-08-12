"""
가상 포트폴리오 (페이퍼 트레이딩) — 1억 원, 하루 단위 매매.

체결 규칙 (docs/RULES.md §3):
  · **장이 열려 있는 동안** AI가 판단하고 리포트를 낸다 → 주문은 **AI가 분석한 그 시세로 즉시 체결**.
      - 🇰🇷 한국장: 매일 15:00 리포트 → 독자는 15:30 마감 전에 같은 가격대로 매수 가능
      - 🇺🇸 미국장: 매일 23:45 리포트(장중) → 독자는 그 자리에서 매수 가능
  · **체결가 = AI가 본 가격**(market.json의 현재가). 가격을 보고 "싸다/비싸다"를 판단했으니 그 가격에 산다.
    (분석가는 27만원을 보고 샀는데 29만원에 체결되는 식이면 판단 자체가 무의미해진다)
  · **룩어헤드 없음**: 지금 가격을 보고 지금 사는 건 정상 거래다. 반칙은 '미래 가격'을 보는 것인데,
    손익은 이 시점 **이후** 가격으로 결정되고 AI는 그걸 볼 수 없다.
  · 주식·ETF 정수 주수 / 암호화폐·원자재 소수 + 체결 시점 환율 기록.

AI 4인: 실행 `python portfolio.py <label> <persona>` (persona=stable|aggressive|normal1|normal2)
상태: _data/portfolio-<persona>.json (holdings/lots/journal/pending_orders/history)
주문: portfolio/orders/<날짜>-<세션>-<persona>.json · 자산곡선: assets/portfolio/equity-<persona>.png
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as _fm

from _rundate import run_date

# 윈도우 콘솔(cp949)에서 경고문의 이모지 때문에 죽지 않도록 (리눅스는 원래 UTF-8)
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

for _f in ("Malgun Gothic", "NanumGothic", "NanumBarunGothic", "AppleGothic"):
    if _f in {f.name for f in _fm.fontManager.ttflist}:
        matplotlib.rcParams["font.family"] = _f
        break
matplotlib.rcParams["axes.unicode_minus"] = False

KST = timezone(timedelta(hours=9))
REPO = Path(__file__).resolve().parent.parent
START_CAPITAL = 100_000_000
KRW_CATEGORIES = {"kr_index", "kr_stock"}
TRADABLE = {"us_stock", "kr_stock", "us_sector", "crypto", "commodity"}
IMMEDIATE = {"crypto", "commodity"}          # 24시간 거래 → 언제든 그 시점 시세로 체결
# 세션별 거래 가능 시장 — 지금 열려 있는 시장의 종목만 거래한다.
# (예: 한국장 시간에 미국 ETF를 사면 며칠 전 미국 종가에 체결되는데, 그 시각엔 그 가격에 살 수 없다)
SESSION_CATS = {"kr": {"kr_stock"}, "us": {"us_stock", "us_sector"}}
SESSION_LABEL = {"kr": "🇰🇷 한국장", "us": "🇺🇸 미국장", "": ""}

# AI 투자자 4명 — 각자 독립 계좌(_data/portfolio-<id>.json)
#   · 성향파 2명(안정·공격) — 모델 opus: 뚜렷한 색깔을 부여한 극단 양 끝
#   · 평범형 2명(1·2)     — 모델 fable: **완전히 동일한 지시문**을 받는 대조군.
#     같은 모델·같은 데이터·같은 프롬프트로 판단이 얼마나 갈리는지(편차) 보기 위한 것이므로
#     둘의 tag도 동일하다. (모델 지정은 daily.yml / run-daily.ps1)
PERSONAS = {
    "stable":     {"name": "안정형",   "emoji": "🛡️", "tag": "가치·방어 · 현금 넉넉 · opus"},
    "aggressive": {"name": "공격형",   "emoji": "🚀", "tag": "성장·모멘텀 · 집중 투자 · opus"},
    "normal1":    {"name": "평범형 1", "emoji": "🙂", "tag": "성향 없음 · 동일 지시문 대조군 · fable"},
    "normal2":    {"name": "평범형 2", "emoji": "🙂", "tag": "성향 없음 · 동일 지시문 대조군 · fable"},
}

# 보유 종목을 페이지에서 🇰🇷/🇺🇸/🌐로 나눠 보여주기 위한 시장 구분.
#  ⚠️ 통화(KRW/USD)로 나누면 안 된다 — 암호화폐·원자재도 USD라서 '미국'으로 잘못 묶인다.
MARKET_OF = {"kr_stock": "kr", "kr_index": "kr", "us_stock": "us", "us_sector": "us"}
MARKET_META = {                                  # 페이지 섹션 제목·정렬 순서
    "kr":  {"label": "🇰🇷 한국", "order": 0},
    "us":  {"label": "🇺🇸 미국", "order": 1},
    "etc": {"label": "🌐 24시간 자산 (암호화폐·원자재)", "order": 2},
}
# 보유 종목 색상 팔레트 — 비중 막대와 목록 행이 같은 색을 쓰도록 파이썬에서 확정한다
# (레이아웃에서 루프 인덱스로 칠하면 한국/미국 섹션을 나눌 때 색이 겹친다)
PALETTE = ["#3ba272", "#e8a33d", "#8b5fd6", "#d3655f", "#4aa3c0", "#c0699d",
           "#7d9a3c", "#c98a4b", "#5f7fd6", "#b05fa8", "#3f9e8c", "#cf7060"]

# 24시간 자산(암호화폐·원자재) 표시 단위 — 나머지 주식·ETF는 "주"
UNIT_OVERRIDE = {"GC=F": "oz", "MGC=F": "oz", "SI=F": "oz", "CL=F": "bbl", "BZ=F": "bbl",
                 "BTC-USD": "BTC", "ETH-USD": "ETH"}


def unit_of(ticker: str, category: str) -> str:
    if ticker in UNIT_OVERRIDE:
        return UNIT_OVERRIDE[ticker]
    if category == "crypto":
        return "개"
    if category == "commodity":
        return "단위"
    return "주"          # 주식·ETF


def qn(q):
    """정수면 int(64), 아니면 소수 4자리(1.9908) — '64.0주' 방지."""
    q = float(q)
    return int(q) if q.is_integer() else round(q, 4)


def load_json(path: Path, default=None):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def won(n):
    return f"{round(n):,}"


def r2(x):
    return round(float(x), 2) if x is not None else None


def next_day(date_str: str) -> str:
    d = datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def price_map(market: dict):
    inst = market.get("instruments", {})
    usdkrw = None
    if "KRW=X" in inst and inst["KRW=X"].get("last"):
        usdkrw = float(inst["KRW=X"]["last"])
    out = {}
    for t, d in inst.items():
        last = d.get("last")
        if last is None:
            continue
        cat = d.get("category", "")
        is_krw = cat in KRW_CATEGORIES
        fx = 1.0 if is_krw else usdkrw
        if not fx:
            continue
        out[t] = {
            "price_krw": float(last) * fx,
            "price_native": float(last),
            "open_native": float(d["open"]) if d.get("open") else None,
            "open_krw": float(d["open"]) * fx if d.get("open") else None,
            "currency": "KRW" if is_krw else "USD",
            "category": cat, "name": d.get("name", t),
            "data_date": d.get("data_date"),
        }
    return out, usdkrw


def exec_buy(holdings, cash, t, info, budget, price_krw, price_native, usdkrw, today, session,
             reason, basis, fractional=False):
    """매수 체결. (성공 시 갱신된 cash, trade기록) 반환. 실패 시 (cash, None).

    `fractional=True`면 소수 단위로 산다 — 지수(^KS11)처럼 '주'라는 개념이 없는 대상용.
    (현재는 `scripts/backtest.py`만 쓴다. 라이브 계좌의 주식·ETF는 항상 정수 주수다.)
    """
    budget = min(float(budget), cash)
    if budget <= 0:
        return cash, None
    if fractional or info["category"] in IMMEDIATE:
        # 24시간 자산(암호화폐·원자재)·지수: 소수 단위 체결이 현실적
        qty = budget / price_krw
        krw = budget
    else:
        # 주식·ETF(한국·미국 공통): 정수 주수만, 잔액은 현금 유지
        qty = int(budget // price_krw)
        if qty < 1:
            return cash, None
        krw = qty * price_krw
    h = holdings.setdefault(t, {"name": info["name"], "qty": 0.0, "cost_krw": 0.0, "lots": []})
    h["qty"] += qty; h["cost_krw"] += krw; h["name"] = info["name"]
    h.setdefault("lots", []).append({
        "date": today, "session": session, "qty": qn(qty),
        "price_krw": round(price_krw), "price_native": round(price_native, 2),
        "currency": info["currency"], "krw": round(krw),
        "fx": round(usdkrw, 2) if info["currency"] == "USD" and usdkrw else None,
        "price_date": info.get("data_date"), "basis": basis,
    })
    is_usd = info["currency"] == "USD"
    trade = {"action": "매수", "ticker": t, "name": info["name"], "krw": round(krw), "krw_str": won(krw),
             "qty": qn(qty), "unit": unit_of(t, info["category"]),
             "price_krw": round(price_krw), "price_str": won(price_krw),
             "price_native_str": (f"${price_native:,.2f}" if is_usd else None),
             "basis": basis, "reason": reason}
    return cash - krw, trade


def exec_sell(holdings, cash, t, info, qty_req, price_krw, today, session, reason, basis):
    h = holdings.get(t)
    if not h or h["qty"] <= 0:
        return cash, None
    qty = min(float(qty_req) if qty_req else h["qty"], h["qty"])
    proceeds = qty * price_krw

    # 원가도 lot과 **같은 방식(선입선출)** 으로 덜어낸다.
    #   ⚠️ 예전엔 원가는 비율로 깎고(평균법) lot은 FIFO로 지워서, 부분 매도 뒤
    #      `cost_krw`(→평단)와 화면의 거래내역 합계가 서로 어긋났다.
    #      이제 `cost_krw == Σ(lot.qty × lot.price_krw)` 가 항상 유지된다.
    avg_before = h["cost_krw"] / h["qty"] if h["qty"] else 0
    lots = h.setdefault("lots", [])
    remain, cost_out = qty, 0.0
    for lot in list(lots):
        if remain <= 1e-9:
            break
        take = min(float(lot["qty"]), remain)
        cost_out += take * float(lot["price_krw"])
        lot["qty"] = round(float(lot["qty"]) - take, 4)
        lot["krw"] = round(lot["qty"] * lot["price_krw"])
        remain -= take
        if lot["qty"] <= 1e-9:
            lots.remove(lot)
    if remain > 1e-9:                    # lot 기록이 불완전한 구버전 상태 — 남은 몫만 평균법
        cost_out += remain * avg_before
    h["cost_krw"] = max(0.0, h["cost_krw"] - cost_out)
    h["qty"] -= qty
    if h["qty"] <= 1e-9:
        holdings.pop(t, None)
    # 매도는 **평단과 실현손익**이 같이 있어야 의미가 읽힌다.
    #   ⚠️ 손익은 **평단 기준**으로 낸다. FIFO 원가(cost_out)로 내면 화면에 같이 뜨는
    #      평단·퍼센트와 부호가 어긋난다("평단보다 싸게 팔았는데 실현 +"). 읽는 사람 기준으로
    #      "평단 대비 얼마"가 유일하게 말이 되는 숫자다. (계좌 원가 자체는 lot과 같이 FIFO)
    pl = qty * (price_krw - avg_before)
    is_usd = info["currency"] == "USD"
    trade = {"action": "매도", "ticker": t, "name": info["name"], "krw": round(proceeds), "krw_str": won(proceeds),
             "qty": qn(qty), "unit": unit_of(t, info["category"]),
             "price_krw": round(price_krw), "price_str": won(price_krw),
             "price_native_str": (f"${info.get('price_native', 0):,.2f}" if is_usd and info.get("price_native") else None),
             "avg_krw": round(avg_before), "avg_str": won(avg_before),
             "pl_krw": round(pl), "pl_str": ("+" if pl >= 0 else "") + won(pl),
             "pl_pct": round((price_krw / avg_before - 1) * 100, 2) if avg_before else 0.0,
             "basis": basis, "reason": reason}
    return cash + proceeds, trade


def main() -> int:
    # 인자: <label> <persona>
    #   label   = kr|us (장중 세션)
    #   persona = stable|aggressive|normal1|normal2 (각자 독립 계좌)
    label = sys.argv[1] if len(sys.argv) > 1 else None
    persona = sys.argv[2] if len(sys.argv) > 2 else "stable"
    if persona not in PERSONAS:
        print(f"알 수 없는 성향: {persona} — {list(PERSONAS)}", file=sys.stderr)
        return 1
    pmeta = PERSONAS[persona]
    # 체결 기준일 = 회차 기준일(RUN_DATE). 워크플로가 회차 시작 시 한 번 확정해 넘긴다.
    #   ⚠️ 여기서 datetime.now()를 쓰면 자정을 넘긴 🇺🇸 세션이 다음 날 폴더를 찾아 주문서를 통째로
    #      흘린다 (2026-07-28·07-30·07-31 US 12건 유실). 재생(replay)용 오버라이드: PF_TODAY·PF_MARKET.
    today = run_date("PF_TODAY")
    mfile = os.environ.get("PF_MARKET")
    orders_dir = REPO / "portfolio" / "orders"

    def unapplied_for(applied_stems, void_stems=()) -> list[Path]:
        """이 성향 앞으로 나왔는데 체결도 결번도 아닌 주문서 (날짜 무관).

        `void_orders` = **결번**. 파이프라인 사고로 끝내 체결되지 않은 회차를 사후 체결하지 않고
        "유실"로 확정 기록한 것이다(docs/RULES.md §4-1). 이미 게시된 수익률을 사후에 바꾸지
        않는다는 원칙에 따른 처리이므로, 미체결 경고 대상에서 제외한다.
        """
        if not orders_dir.exists():
            return []
        done = set(applied_stems) | set(void_stems)
        return sorted(p for p in orders_dir.glob(f"*-{persona}.json") if p.stem not in done)

    market = load_json(Path(mfile)) if mfile else load_json(REPO / "data" / today / "market.json")
    if not market:
        src = mfile or f"data/{today}/market.json"
        # 주문서가 이미 나와 있는데 시세가 없다 = 그 주문은 영영 체결되지 않는다. 조용히 넘어가면 안 된다.
        prior = load_json(REPO / "_data" / f"portfolio-{persona}.json") or {}
        # 이번 회차 주문서만 본다 — 과거 유실분까지 여기서 실패로 처리하면 이후 회차가 영영 막힌다
        # (그건 아래 6)의 경고와 verify_run.py가 따로 알린다).
        stuck = [p for p in unapplied_for(prior.get("applied_orders", []), prior.get("void_orders", []))
                 if p.stem.startswith(today)]
        print(f"[{persona}] market.json 없음({src})", file=sys.stderr)
        if stuck:
            print(f"[{persona}] ❌ 체결 못 한 주문서 {len(stuck)}건: "
                  + ", ".join(p.stem for p in stuck), file=sys.stderr)
            print(f"[{persona}] ❌ RUN_DATE({today})와 수집 날짜가 어긋났을 가능성이 높다 — 워크플로 로그 확인 필요", file=sys.stderr)
            return 1
        print(f"[{persona}] 미체결 주문서 없음 — 갱신 생략", file=sys.stderr)
        return 0
    prices, usdkrw = price_map(market)

    state_path = REPO / "_data" / f"portfolio-{persona}.json"
    state = load_json(state_path)
    if not state:
        state = {"start_date": today, "start_capital": START_CAPITAL, "currency": "KRW",
                 "cash": START_CAPITAL, "holdings": {}, "applied_orders": [],
                 "pending_orders": [], "journal": [], "history": []}
        print(f"[{persona}] 포트폴리오 신규 개설: {START_CAPITAL:,}원 ({today})")

    holdings = state.get("holdings", {})
    cash = float(state.get("cash", START_CAPITAL))
    applied = state.setdefault("applied_orders", [])
    void = state.setdefault("void_orders", [])          # 결번 — 사고로 유실 확정된 회차 (RULES §4-1)
    pending = state.setdefault("pending_orders", [])
    journal = state.setdefault("journal", [])

    # ── 1) 새 주문서 접수 → AI가 분석한 그 시세로 즉시 체결 ──
    # (가격을 보고 판단했으니 그 가격에 산다. 장중이라 독자도 같은 가격대로 실제 매수 가능.
    #  룩어헤드 아님: 손익은 이 시점 '이후' 가격으로 결정되고 AI는 그걸 못 본다.)
    for od_unused in list(pending):
        pending.remove(od_unused)          # 구방식 잔여 대기주문 정리(있으면)
    # ⚠️ 결번(void_orders)은 "유실 확정"이라 다시 체결하지 않는다.
    #    이걸 빼면 계좌를 처음부터 재생성할 때 과거 유실분이 되살아나 기록이 달라진다.
    _done = set(applied) | set(void)
    new_files = sorted(p for p in orders_dir.glob(f"{today}-*-{persona}.json") if p.stem not in _done) if orders_dir.exists() else []
    for opath in new_files:
        doc = load_json(opath, {})
        session = doc.get("session") or (opath.stem.split("-")[-1] if opath.stem.count("-") > 2 else "")
        placed_view, trades = [], []
        for o in doc.get("orders", []):
            act = (o.get("action") or "").lower()
            t = o.get("ticker")
            if act == "hold" or not t:
                if act == "hold":
                    placed_view.append({"action": "유지", "name": "-", "detail": o.get("reason", "")})
                continue
            info = prices.get(t)
            if not info:
                print(f"  건너뜀: {t} 시세 없음", file=sys.stderr); continue
            if act == "buy" and info["category"] not in TRADABLE:
                print(f"  건너뜀: {info['name']} 매수불가 분류", file=sys.stderr); continue
            # 세션 ≠ 그 종목의 시장이면 거래 불가 (24시간 자산은 어느 세션이든 허용)
            cat = info["category"]
            if cat not in IMMEDIATE and session in SESSION_CATS and cat not in SESSION_CATS[session]:
                print(f"  건너뜀: {info['name']} — '{session}' 세션에선 거래 불가(그 시장은 마감 종가가 오래됨)", file=sys.stderr)
                continue
            basis = f"{info.get('data_date')} 리포트 시세" if cat not in IMMEDIATE else "즉시(24h)"
            if act == "buy":
                cash, tr = exec_buy(holdings, cash, t, info, o.get("krw", 0),
                                    info["price_krw"], info["price_native"], usdkrw,
                                    today, session, o.get("reason", ""), basis)
            else:
                cash, tr = exec_sell(holdings, cash, t, info, o.get("qty"),
                                     info["price_krw"], today, session, o.get("reason", ""), basis)
            if tr:
                trades.append(tr)
        applied.append(opath.stem)
        journal.append({"date": today, "session": session, "comment": doc.get("comment", ""),
                        "placed": placed_view, "trades": trades})

    # ── 3) 재평가 ──
    hold_view, holdings_value = [], 0.0
    for t, h in holdings.items():
        info = prices.get(t)
        if not info:
            continue
        pr = info["price_krw"]
        val = h["qty"] * pr
        holdings_value += val
        avg = h["cost_krw"] / h["qty"] if h["qty"] else 0
        is_usd = info["currency"] == "USD"
        cost_native = sum(l["qty"] * l["price_native"] for l in h.get("lots", [])) if is_usd else 0
        avg_native = cost_native / h["qty"] if (is_usd and h["qty"]) else 0
        lots_view = [{**lot, "qty": qn(lot["qty"]), "krw_str": won(lot["krw"]), "price_krw_str": won(lot["price_krw"]),
                      "native_str": (f"${lot['price_native']:,.2f}" if lot.get("currency") == "USD" else None)}
                     for lot in h.get("lots", [])]
        pl_krw = val - h["cost_krw"]
        hold_view.append({
            "ticker": t, "name": h["name"], "qty": qn(h["qty"]),
            "unit": unit_of(t, info["category"]), "currency": info["currency"],
            "category": info["category"],
            "market": MARKET_OF.get(info["category"], "etc"),   # 🇰🇷/🇺🇸/🌐 섹션 구분
            "cost_str": won(h["cost_krw"]),
            "pl_krw_str": ("+" if pl_krw >= 0 else "") + won(pl_krw),
            "avg_krw": round(avg), "avg_str": won(avg),
            "avg_native_str": (f"${avg_native:,.2f}" if is_usd and avg_native else None),
            "price_krw": round(pr), "price_str": won(pr),
            # 숫자 원본도 같이 내려준다 — holding_charts.py가 문자열을 되파싱하지 않고,
            # 차트의 '현재가·수익률'이 페이지와 정확히 같은 값을 쓰게 하기 위함.
            "price_native": r2(info["price_native"]) if is_usd else None,
            "avg_native": r2(avg_native) if (is_usd and avg_native) else None,
            "price_native_str": (f"${info['price_native']:,.2f}" if is_usd else None),
            "price_date": info.get("data_date"), "value_krw": round(val),
            "pl_pct": round((pr / avg - 1) * 100, 2) if avg else 0.0,
            "lots": lots_view,
        })
    # 시장(🇰🇷→🇺🇸→🌐) 먼저, 그 안에서 평가액 큰 순 — 페이지 섹션 순서와 일치시킨다
    hold_view.sort(key=lambda x: (MARKET_META[x["market"]]["order"], -x["value_krw"]))
    total = cash + holdings_value
    ret_pct = (total / START_CAPITAL - 1) * 100
    for i, hv in enumerate(hold_view):
        hv["weight_pct"] = round(hv["value_krw"] / total * 100, 1) if total else 0
        hv["value_str"] = won(hv["value_krw"])
        hv["color"] = PALETTE[i % len(PALETTE)]      # 비중 막대와 목록 행이 같은 색을 쓰게 고정

    # 시장별 소계 — 페이지에서 "🇰🇷 한국 · 3종목 · 4,120만원 (41.2%)" 섹션 헤더로 쓴다.
    # ⚠️ 보유 목록 자체는 담지 않는다(중복 저장 시 holdings_view와 어긋난다).
    #    레이아웃이 holdings_view를 market으로 필터링해 같은 dict를 쓰게 한다.
    by_market = []
    for mkt, meta in sorted(MARKET_META.items(), key=lambda kv: kv[1]["order"]):
        rows = [hv for hv in hold_view if hv["market"] == mkt]
        if not rows:
            continue
        v = sum(hv["value_krw"] for hv in rows)
        by_market.append({
            "market": mkt, "label": meta["label"], "count": len(rows),
            "value_krw": round(v), "value_str": won(v),
            "weight_pct": round(v / total * 100, 1) if total else 0,
        })

    # 대기 주문 없음(종가 즉시체결) — 페이지 호환 위해 빈 목록 유지
    pending_view = []

    # ── 4) 히스토리 (일별 스냅샷) — 매 실행(장중 리포트 시점)마다 확정 기록 ──
    hist = state.get("history", [])
    finalize = True                                       # 실행 시점이 이미 종가 → 항상 확정
    prev_marks = [h for h in hist if h["date"] != today]
    prev_total = prev_marks[-1]["total_value"] if prev_marks else START_CAPITAL
    day_chg_pct = round((total / prev_total - 1) * 100, 2) if prev_total else 0.0
    if finalize:
        hist = prev_marks + [{
            "date": today, "total_value": round(total), "total_value_str": won(total),
            "return_pct": round(ret_pct, 2), "day_chg_pct": day_chg_pct, "cash": round(cash),
            "asof": {"kr": "🇰🇷 장중 리포트 시점", "us": "🇺🇸 장중 리포트 시점"}.get(label, "리포트 시점"),
            "holdings": [{"name": hv["name"], "value_str": hv["value_str"], "weight_pct": hv["weight_pct"], "pl_pct": hv["pl_pct"]} for hv in hold_view],
        }]
        hist.sort(key=lambda x: x["date"])

    state.update({
        "cash": round(cash), "holdings": holdings, "updated": today,
        "total_value": round(total), "holdings_value": round(holdings_value),
        "return_pct": round(ret_pct, 2), "usdkrw": round(usdkrw, 2) if usdkrw else None,
        "holdings_view": hold_view, "by_market": by_market, "history": hist,
        "pending_orders": pending, "pending_view": pending_view,
        "total_value_str": won(total), "cash_str": won(cash),
        "holdings_value_str": won(holdings_value), "start_capital_str": won(START_CAPITAL),
        "gain_str": ("+" if total >= START_CAPITAL else "") + won(total - START_CAPITAL),
        "cash_weight_pct": round(cash / total * 100, 1) if total else 0,
        "day_chg_pct": day_chg_pct, "days": len(hist),
        "priced_at": market.get("generated_at_kst", ""),
        "eval_note": "🇰🇷 15:00 · 🇺🇸 23:45 발행 시점 시세로 체결",
        "persona": persona, "persona_name": pmeta["name"],
        "persona_emoji": pmeta["emoji"], "persona_tag": pmeta["tag"],
    })
    state["journal_view"] = list(reversed(journal))
    state["history_view"] = list(reversed(hist))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 5) 자산 곡선 ──
    chart_dir = REPO / "assets" / "portfolio"
    chart_dir.mkdir(parents=True, exist_ok=True)
    dates = [h["date"][5:] for h in hist]
    vals = [h["total_value"] for h in hist]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(dates, vals, color="#175cd3", linewidth=2, marker="o", markersize=4)
    ax.axhline(START_CAPITAL, color="#94a3b8", linestyle="--", linewidth=1, label="시작 (1억)")
    ax.fill_between(range(len(dates)), START_CAPITAL, vals, alpha=0.08, color="#175cd3")
    ax.set_title(f"[{pmeta['name']}] 가상 포트폴리오 자산 추이 (장중 리포트 시점 평가)  ·  {total:,.0f}원 ({ret_pct:+.2f}%)", fontsize=13, fontweight="bold")
    ax.yaxis.set_major_formatter(lambda x, _: f"{x/1e8:.2f}억")
    ax.legend(fontsize=9); ax.grid(alpha=0.25)
    if len(dates) > 12:
        ax.set_xticks(range(0, len(dates), max(1, len(dates) // 10)))
    fig.autofmt_xdate(rotation=0)
    fig.tight_layout()
    fig.savefig(chart_dir / f"equity-{persona}.png", dpi=110)
    plt.close(fig)

    print(f"[{persona}] 총 {total:,.0f}원 ({ret_pct:+.2f}%) · 현금 {cash:,.0f} · 보유 {len(hold_view)}종목 (리포트 시세 체결)")

    # ── 6) 유실 감시 — 과거에 나왔는데 끝내 체결되지 않은 주문서 ──
    # 실패시키지는 않는다(이미 지난 회차는 되돌릴 수 없고, 매번 죽으면 이후 회차까지 막힌다).
    # 대신 크게 찍어서 워크플로 점검 스텝과 사람이 바로 알아채게 한다.
    orphans = [p.stem for p in unapplied_for(applied, void)]
    if orphans:
        print(f"[{persona}] ⚠️ 미체결로 남은 과거 주문서 {len(orphans)}건: " + ", ".join(orphans), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
