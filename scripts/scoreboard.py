"""
🧮 AI 채점판 — "이 AI들이 진짜 잘하는가"를 숫자로 판정한다.

왜 필요한가 (2026-08-05 신설)
  계좌 수익률만 보면 **하루 1표본**이라 12일이 지나도 실력인지 운인지 알 수 없다.
  그런데 4인은 매 회차 여러 종목을 콜한다 — **종목 콜은 하루 20~40표본**이다.
  게다가 주문서(`portfolio/orders/`)와 시세(`data/*/market.json`)가 전부 커밋돼 있어
  **과거 전부를 소급 채점**할 수 있다. 표본이 10배 이상 늘어난다.

채점 방법
  · 각 매수/매도 콜에 대해, 콜 시점(체결가) → N회차 뒤 가격의 수익률을 구하고
    **같은 기간 벤치마크(🇰🇷 코스피 / 🇺🇸 S&P500) 수익률을 뺀다** = 초과수익.
    시장이 오르내린 몫을 제거해야 "종목을 고르는 실력"만 남는다.
  · 매수는 초과수익이 +면 적중. 매도는 −면 적중(팔길 잘했다).
  · 지평선을 1·3·5회차와 '현재까지'로 나눈다 — 짧게만 맞고 길게 틀리는지 보기 위함.

같이 재는 것 (숫자 하나로는 못 보는 것들)
  · **콜 중복도**: 4인이 같은 종목을 얼마나 겹쳐 사는가. 겹칠수록 '4개의 뇌'가
    사실은 하나이고, 계좌를 나눠도 분산이 안 된다는 뜻이다.
  · **노이즈 바닥**: 평범형 1·2는 지시문·모델이 동일하다. 둘의 일간 수익률 차이가
    곧 "아무 이유 없이 갈리는 폭"이다. 어떤 초과수익도 이 폭을 넘어야 의미가 있다.

⚠️ 한계 (해석할 때 반드시 감안)
  · 4인의 콜이 서로 겹치면 **독립 표본이 아니다.** 콜 93건이 곧 93표본이 아니다.
  · 스냅샷 회차가 적으면 긴 지평선의 표본이 적다.
  · 벤치마크는 지수이고 콜은 개별 종목이라 변동성이 다르다(베타 미보정).

실행:  python scripts/scoreboard.py        →  _data/scoreboard.json + 콘솔 요약
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from _rundate import run_date

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent.parent
PERSONAS = ("stable", "aggressive", "normal1", "normal2")
PERSONA_NAME = {"stable": "🛡️ 안정형", "aggressive": "🚀 공격형",
                "normal1": "🙂 평범형 1", "normal2": "🙂 평범형 2"}
# 카테고리별 벤치마크 — 그 종목이 속한 시장이 그 기간에 얼마나 움직였는가
BENCH = {"kr_stock": "^KS11", "kr_index": "^KS11",
         "us_stock": "^GSPC", "us_sector": "^GSPC"}
BENCH_NAME = {"^KS11": "코스피", "^GSPC": "S&P500"}
HORIZONS = [("h1", 1, "1회차 뒤"), ("h3", 3, "3회차 뒤"),
            ("h5", 5, "5회차 뒤"), ("now", None, "현재까지")]


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def pct(a, b):
    return (b / a - 1) * 100 if a else None


def main() -> int:
    today = run_date()

    # ── 시세 스냅샷 (회차 = 하루, market.json이 그 날의 최종 마크) ──
    snaps: dict[str, dict] = {}
    for f in sorted((REPO / "data").glob("*/market.json")):
        m = load(f)
        if m and m.get("instruments"):
            snaps[f.parent.name] = m["instruments"]
    dates = sorted(snaps)
    if len(dates) < 2:
        print("스냅샷이 2회차 미만 — 채점 생략", file=sys.stderr)
        return 0

    def price(d: str, t: str):
        i = snaps.get(d, {}).get(t)
        return float(i["last"]) if i and i.get("last") is not None else None

    def ahead(d: str, n: int | None):
        """d로부터 n회차 뒤. n=None이면 마지막 회차(현재까지)."""
        i = dates.index(d)
        j = len(dates) - 1 if n is None else min(i + n, len(dates) - 1)
        return dates[j] if j > i else None

    # ── 콜 단위 채점 ──────────────────────────────────────────
    calls: list[dict] = []
    same_day: dict[tuple[str, str], set] = defaultdict(set)   # (날짜세션, 티커) → 매수한 성향들
    for f in sorted((REPO / "portfolio" / "orders").glob("*.json")):
        doc = load(f)
        if not doc:
            continue
        d0 = doc.get("date")
        persona = doc.get("persona") or f.stem.split("-")[-1]
        session = doc.get("session", "")
        if d0 not in snaps or persona not in PERSONAS:
            continue
        for o in doc.get("orders", []):
            act, t = o.get("action"), o.get("ticker")
            if act not in ("buy", "sell") or not t:
                continue
            info = snaps[d0].get(t)
            if not info:
                continue
            bench = BENCH.get(info.get("category", ""))
            p0 = price(d0, t)
            if not (p0 and bench):
                continue
            if act == "buy":
                same_day[(f"{d0}-{session}", t)].add(persona)
            row = {"persona": persona, "date": d0, "session": session, "ticker": t,
                   "name": info.get("name", t), "action": act,
                   "bench": BENCH_NAME.get(bench, bench), "reason": o.get("reason", ""), "r": {}}
            for key, n, _ in HORIZONS:
                d1 = ahead(d0, n)
                if not d1:
                    continue
                p1, k0, k1 = price(d1, t), price(d0, bench), price(d1, bench)
                if not (p1 and k0 and k1):
                    continue
                exc = pct(p0, p1) - pct(k0, k1)
                # 매도는 부호를 뒤집는다 — 팔고 나서 시장 대비 더 빠졌으면 잘 판 것
                signed = exc if act == "buy" else -exc
                row["r"][key] = {"excess": round(signed, 2), "hit": signed > 0,
                                 "to": d1, "stock": round(pct(p0, p1), 2),
                                 "bench_pct": round(pct(k0, k1), 2)}
            if row["r"]:
                calls.append(row)

    if not calls:
        print("채점할 콜 없음", file=sys.stderr)
        return 0

    # ── 집계 ─────────────────────────────────────────────────
    def agg(rows, key):
        v = [r["r"][key] for r in rows if key in r["r"]]
        if not v:
            return None
        ex = [x["excess"] for x in v]
        return {"n": len(v), "hit_pct": round(sum(1 for x in v if x["hit"]) / len(v) * 100, 1),
                "avg_excess": round(sum(ex) / len(ex), 2),
                "median_excess": round(statistics.median(ex), 2)}

    by_persona = {}
    for p in PERSONAS:
        rows = [c for c in calls if c["persona"] == p]
        if not rows:
            continue
        by_persona[p] = {"name": PERSONA_NAME[p], "calls": len(rows),
                         **{k: agg(rows, k) for k, _, _ in HORIZONS}}
    overall = {"calls": len(calls), **{k: agg(calls, k) for k, _, _ in HORIZONS}}

    # ── 겹침도 — '4개의 뇌'가 실제로 몇 개인가 ─────────────────
    # 두 가지를 따로 잰다. 둘이 다르면 의미가 다르다:
    #   · 주문 겹침: 같은 날 같은 종목을 동시에 샀나 (타이밍까지 같은가)
    #   · 보유 겹침: 결국 같은 포트폴리오에 도달했나 (분산이 되는가)
    #     ⚠️ 분산 여부를 판정하는 건 **보유 겹침**이다. 경로가 달라도 종착지가 같으면
    #        계좌를 4개로 나눈 의미가 없다.
    dup = [len(v) for v in same_day.values()]
    order_ov = {
        "buy_slots": len(dup),
        "shared_2plus_pct": round(sum(1 for x in dup if x >= 2) / len(dup) * 100, 1) if dup else 0,
        "shared_all4_pct": round(sum(1 for x in dup if x >= 4) / len(dup) * 100, 1) if dup else 0,
    }
    held = {}
    for p in PERSONAS:
        st = load(REPO / "_data" / f"portfolio-{p}.json") or {}
        held[p] = {h["ticker"] for h in st.get("holdings_view", [])}
    pairs, jac = [], []
    for i, a in enumerate(PERSONAS):
        for b in PERSONAS[i + 1:]:
            u = held.get(a, set()) | held.get(b, set())
            if not u:
                continue
            j = len(held[a] & held[b]) / len(u) * 100
            jac.append(j)
            pairs.append({"pair": f"{PERSONA_NAME[a]} × {PERSONA_NAME[b]}",
                          "shared": sorted(held[a] & held[b]), "jaccard_pct": round(j, 1)})
    everyone = set.intersection(*[held[p] for p in PERSONAS if held.get(p)]) if all(held.get(p) for p in PERSONAS) else set()
    overlap = {**order_ov,
               "holdings_jaccard_avg_pct": round(sum(jac) / len(jac), 1) if jac else None,
               "holdings_pairs": pairs,
               "held_by_all": sorted(everyone)}

    # ── 노이즈 바닥 — 동일 지시문 2인이 아무 이유 없이 갈리는 폭 ──
    h = {}
    for p in ("normal1", "normal2"):
        st = load(REPO / "_data" / f"portfolio-{p}.json") or {}
        h[p] = {x["date"]: x.get("day_chg_pct", 0) for x in st.get("history", [])}
    common = sorted(set(h.get("normal1", {})) & set(h.get("normal2", {})))
    gaps = [abs(h["normal1"][d] - h["normal2"][d]) for d in common]
    noise = {"days": len(gaps),
             "avg_daily_gap": round(sum(gaps) / len(gaps), 2) if gaps else None,
             "max_daily_gap": round(max(gaps), 2) if gaps else None}

    # ── 계좌 대 기준선 — 이 프로젝트의 헤드라인 ─────────────────
    # "다 손해"처럼 보여도 시장이 더 빠졌으면 이긴 것이다. 기준선(코스피 매수 후 보유)이
    # 그 눈금이다. ⚠️ 계좌마다 개시일이 다르므로 **각자의 개시일 기준으로** 기준선을 잘라 비교한다.
    bench_state = load(REPO / "_data" / "portfolio-bench.json") or {}
    bench_hist = {x["date"]: x["total_value"] for x in bench_state.get("history", [])}
    bdates = sorted(bench_hist)
    vs_bench = []
    if bdates:
        for p in PERSONAS:
            st = load(REPO / "_data" / f"portfolio-{p}.json") or {}
            if not st.get("history"):
                continue
            start = st["history"][0]["date"]
            base = [d for d in bdates if d >= start]
            if not base:
                continue
            b0, b1 = bench_hist[base[0]], bench_hist[bdates[-1]]
            bret = (b1 / b0 - 1) * 100 if b0 else 0.0
            r = float(st.get("return_pct", 0))
            vs_bench.append({"persona": PERSONA_NAME[p], "id": p, "since": start,
                             "return_pct": round(r, 2), "bench_pct": round(bret, 2),
                             "excess_pct": round(r - bret, 2), "beat": r > bret,
                             "days": st.get("days", 0)})
    beat_n = sum(1 for v in vs_bench if v["beat"])

    # ── 최고/최악 콜 ──────────────────────────────────────────
    scored = [c for c in calls if "now" in c["r"]]
    scored.sort(key=lambda c: c["r"]["now"]["excess"])
    def brief(c):
        return {"persona": PERSONA_NAME[c["persona"]], "date": c["date"], "action": "매수" if c["action"] == "buy" else "매도",
                "name": c["name"], "excess": c["r"]["now"]["excess"], "reason": c["reason"][:40]}
    worst = [brief(c) for c in scored[:5]]
    best = [brief(c) for c in reversed(scored[-5:])]

    out = {
        "generated": today, "snapshots": len(dates),
        "period": {"from": dates[0], "to": dates[-1]},
        "horizons": [{"key": k, "label": lb} for k, _, lb in HORIZONS],
        "overall": overall, "by_persona": by_persona,
        "overlap": overlap, "noise": noise,
        "vs_bench": vs_bench, "beat_bench": beat_n, "accounts": len(vs_bench),
        "best": best, "worst": worst,
        "note": ("초과수익 = 종목 수익률 − 같은 기간 벤치마크(코스피/S&P500). "
                 "매도는 부호를 뒤집어 채점(팔고 나서 더 빠졌으면 적중). "
                 "⚠️ 4인의 콜이 겹치면 독립 표본이 아니다 — 콜 수 ≠ 표본 수."),
    }
    (REPO / "_data").mkdir(exist_ok=True)
    (REPO / "_data" / "scoreboard.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 콘솔 요약 ─────────────────────────────────────────────
    print(f"🧮 AI 채점판 — {dates[0]} ~ {dates[-1]} ({len(dates)}회차) · 종목 콜 {len(calls)}건\n")
    for key, _, label in HORIZONS:
        if not overall.get(key):
            continue
        print(f"■ {label}")
        print(f"   {'계좌':13}{'콜':>5}{'적중률':>9}{'평균 초과':>11}")
        for p, v in by_persona.items():
            if v.get(key):
                print(f"   {PERSONA_NAME[p]:13}{v[key]['n']:>5}{v[key]['hit_pct']:>8.0f}%{v[key]['avg_excess']:>+10.2f}%p")
        o = overall[key]
        print(f"   {'전체':13}{o['n']:>5}{o['hit_pct']:>8.0f}%{o['avg_excess']:>+10.2f}%p\n")
    if vs_bench:
        print(f"■ 계좌 대 기준선 (📊 코스피 매수 후 보유) — **{beat_n}승 {len(vs_bench)-beat_n}패**")
        print(f"   {'계좌':13}{'개시':>12}{'수익률':>9}{'기준선':>9}{'초과':>10}")
        for v in vs_bench:
            print(f"   {v['persona']:13}{v['since']:>12}{v['return_pct']:>+8.2f}%{v['bench_pct']:>+8.2f}%{v['excess_pct']:>+9.2f}%p")
        print("   → 절대 손익이 아니라 **기준선 대비**로 본다. 시장이 더 빠졌으면 손해여도 이긴 것이다\n")
    print(f"■ 주문 겹침 — 매수 슬롯 {overlap['buy_slots']}개 중 "
          f"2인 이상 동시 매수 {overlap['shared_2plus_pct']}% · 4인 전원 {overlap['shared_all4_pct']}%")
    if overlap["holdings_jaccard_avg_pct"] is not None:
        print(f"■ 보유 겹침 — 계좌 쌍 평균 {overlap['holdings_jaccard_avg_pct']}% (자카드)")
        if overlap["held_by_all"]:
            names = [c["name"] for t in overlap["held_by_all"]
                     for c in calls if c["ticker"] == t][:1] or overlap["held_by_all"]
            print(f"   4인 전원 보유: {', '.join(sorted(set(str(x) for x in overlap['held_by_all'])))}")
        print(f"   → 판정은 **보유 겹침**으로 한다. 경로가 달라도 종착지가 같으면 분산이 아니다")
    if noise["avg_daily_gap"] is not None:
        print(f"■ 노이즈 바닥 — 동일 지시문 평범형 1·2의 일간 수익률 차이: "
              f"평균 {noise['avg_daily_gap']}%p · 최대 {noise['max_daily_gap']}%p ({noise['days']}일)")
        print(f"   → 어떤 초과수익도 이 폭을 넘어야 '실력'이라 말할 수 있다")
    print(f"\n저장: _data/scoreboard.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
