"""
회차 기준일(RUN_DATE) — 파이프라인 전 단계가 **같은 하루**를 보게 만드는 단일 기준.

왜 필요한가 (2026-08-04 사고 재발 방지)
  각 스크립트가 제각기 `datetime.now(KST)`로 날짜를 계산하면, 실행이 자정을 넘길 때
  단계마다 날짜가 갈린다. 실제로 🇺🇸 세션(23:30 시작 · 파이프라인 ~30분)이 자정을 넘기면서
  수집은 `data/07-30/`에 쓰고 체결은 `data/07-31/`을 찾는 일이 반복됐고,
  그 결과 **07-28·07-30·07-31 US 주문서 12개가 체결되지 않고 유실**됐다.

규칙
  · 워크플로가 회차 시작 시점에 KST 날짜를 한 번 확정해 `RUN_DATE`로 넘긴다.
  · 모든 스크립트는 이 함수만 쓴다. 직접 `datetime.now()`로 날짜를 만들지 않는다.
  · 로컬에서 인자 없이 돌리면 지금 KST 날짜로 fallback (기존 동작과 동일).
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def run_date(*env_names: str) -> str:
    """회차 기준일 'YYYY-MM-DD'. 우선순위: 지정 환경변수 → RUN_DATE → 현재 KST 날짜."""
    for name in (*env_names, "RUN_DATE"):
        v = (os.environ.get(name) or "").strip()
        if not v:
            continue
        if not _DATE_RE.match(v):
            # 메시지에 em dash·이모지를 쓰지 않는다 — 이 예외는 콘솔 인코딩 설정보다 먼저 터질 수 있고,
            # 윈도우 cp949에서는 그 자체가 UnicodeEncodeError로 바뀌어 원인을 가린다.
            raise SystemExit(f"{name}={v!r} 형식 오류: 'YYYY-MM-DD' 여야 한다")
        return v
    return datetime.now(KST).strftime("%Y-%m-%d")
