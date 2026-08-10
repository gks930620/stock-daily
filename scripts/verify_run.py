"""
회차 산출물 점검 — "초록불인데 결과물이 없다"를 막는 마지막 관문.

왜 필요한가 (2026-08-04 사고 재발 방지)
  🇺🇸 세션이 자정을 넘기면 portfolio.py가 다음 날 폴더를 찾다 실패하고도 정상 종료(0)했다.
  워크플로는 계속 초록불이었고, **07-28·07-30·07-31 US 주문서 12건이 체결되지 않은 채**
  3주 가까이 아무도 몰랐다. 이제 회차 끝에서 아래를 전부 확인하고, 하나라도 어긋나면 죽는다.

점검 항목 (RUN_DATE·MODE 기준)
  1. 시세      data/<날짜>/market.json · market-<세션>.json
  2. 리포트    _posts/<날짜>-<세션>-market.md  (front matter의 date가 그 날짜인지까지)
  3. 주문서    portfolio/orders/<날짜>-<세션>-<성향>.json × 4인
  4. 체결      각 주문서가 _data/portfolio-<성향>.json 의 applied_orders 에 들어갔는지
  5. 유실이력  과거에 나왔는데 끝내 체결되지 않은 주문서가 남아 있는지

실행:  python scripts/verify_run.py <kr|us>        (RUN_DATE 환경변수 사용)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from _rundate import run_date

# 윈도우 콘솔 기본 코드페이지(cp949)는 이모지·em dash를 못 찍고 죽는다.
# 리눅스(Actions)는 UTF-8이라 무관하지만, 로컬 백업 실행도 같은 코드를 쓴다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent.parent
PERSONAS = ("stable", "aggressive", "normal1", "normal2")   # AI 매니저 4인


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("kr", "us"):
        print(f"사용법: verify_run.py <kr|us> (받은 값: {mode!r})", file=sys.stderr)
        return 2
    today = run_date()
    errors: list[str] = []
    warns: list[str] = []
    print(f"▶ 회차 점검 — {today} / {mode}\n")

    # 1) 시세
    for rel in (f"data/{today}/market.json", f"data/{today}/market-{mode}.json"):
        p = REPO / rel
        ok = p.exists() and load(p) is not None
        print(f"  {'OK ' if ok else 'ERR'} 시세      {rel}")
        if not ok:
            errors.append(f"시세 파일 없음/손상: {rel}")

    # 2) 리포트 (+ front matter 날짜가 이 회차인지)
    post = REPO / "_posts" / f"{today}-{mode}-market.md"
    if not post.exists():
        print(f"  ERR 리포트    _posts/{post.name}")
        errors.append(f"리포트 없음: _posts/{post.name}")
    else:
        head = post.read_text(encoding="utf-8")[:400]
        dated = f"date: {today} " in head
        print(f"  {'OK ' if dated else 'ERR'} 리포트    _posts/{post.name}")
        if not dated:
            errors.append(f"리포트 front matter의 date가 {today}가 아니다: _posts/{post.name}")

    # 3~4) 주문서 + 체결 반영
    #   ⚠️ 두 가지를 **구분**한다. 성격이 다르다:
    #     · 주문서가 아예 없다   = 매니저 세션 실패. 이미 워크플로가 재시도하고 경고를 띄웠고,
    #       2명 미만이면 거기서 죽는다 → 여기선 **경고**로 충분하다(시끄럽게 실패한 일).
    #     · 주문서는 있는데 미반영 = **조용한 유실**. 이게 §4-1에서 3주간 아무도 몰랐던 그 버그다
    #       → 반드시 **실패**시킨다.
    present = 0
    for p in PERSONAS:
        stem = f"{today}-{mode}-{p}"
        opath = REPO / "portfolio" / "orders" / f"{stem}.json"
        state = load(REPO / "_data" / f"portfolio-{p}.json") or {}
        applied = set(state.get("applied_orders", []))
        if stem in set(state.get("void_orders", [])):
            print(f"  ERR 체결      {stem} — 결번으로 표시된 회차를 다시 실행했다")
            errors.append(f"결번 회차 재실행: {stem} (void_orders에 있는데 또 돌았다)")
            continue
        if not opath.exists():
            print(f"  --  주문서    {stem}.json 없음 (세션 실패로 이번 회차 불참)")
            warns.append(f"{p}: 이번 회차 주문서 없음 — 매니저 세션 실패")
            continue
        present += 1
        if stem in applied:
            print(f"  OK  체결      {stem}")
        else:
            print(f"  ERR 체결      {stem} — 주문서는 있는데 계좌에 반영 안 됨")
            errors.append(f"미체결: {stem} (RUN_DATE 불일치 또는 portfolio.py 실패)")
    if present == 0:
        print("  ERR 주문서    4인 전원 없음")
        errors.append("매니저 주문서가 하나도 없다 — 리포트의 근거가 없는 회차다")

    # 5) 과거 유실 이력
    odir = REPO / "portfolio" / "orders"
    if odir.exists():
        for p in PERSONAS:
            state = load(REPO / "_data" / f"portfolio-{p}.json") or {}
            # 결번(void_orders)은 '유실 확정'으로 이미 처리된 회차라 경고 대상이 아니다 (RULES §4-1)
            done = set(state.get("applied_orders", [])) | set(state.get("void_orders", []))
            old = [f.stem for f in sorted(odir.glob(f"*-{p}.json"))
                   if f.stem not in done and not f.stem.startswith(today)]
            if old:
                warns.append(f"{p}: 미체결로 남은 과거 주문서 {len(old)}건 — {', '.join(old)}")

    print()
    for w in warns:
        print(f"  ⚠️ {w}")
    if errors:
        print(f"\n❌ 회차 점검 실패 — {len(errors)}건", file=sys.stderr)
        for e in errors:
            print(f"   · {e}", file=sys.stderr)
        return 1
    print(f"\n✅ 회차 점검 통과 — 리포트 + 매니저 {present}/{len(PERSONAS)}인 주문·체결 정합 ({today} {mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
