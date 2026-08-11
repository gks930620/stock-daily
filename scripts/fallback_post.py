"""
📄 실패 안내글 생성 — 회차가 깨졌을 때 **빈칸 대신 사실을 남긴다**.

왜 코드가 쓰는가
  내용이 정해진 문구다. 판단할 것도, 생성할 것도 없다.
  게다가 이 글이 필요한 상황은 **AI를 못 쓰는 상황**(사용량 한도 등)이라
  AI에게 맡기면 정작 필요할 때 못 쓴다. 프로젝트 원칙 그대로 — 사실은 스크립트로.

왜 필요한가 (2026-08-05)
  KR 회차가 사용량 한도로 실패하자 사이트에 그날이 **그냥 비었다.** 독자는 왜 없는지 알 수 없고,
  운영자도 목록만 봐서는 "안 돈 건지 실패한 건지" 구분이 안 된다. 빈칸보다 사실이 낫다.

실행:
  python scripts/fallback_post.py <kr|us> --reason usage \
      --detail "resets 5:30am (UTC)" --run-url https://github.com/.../runs/123

  · 이미 그 회차 글이 있으면 **덮어쓰지 않는다**(정상 발행 뒤 후속 단계가 깨진 경우).
  · front matter는 정상 글과 같은 계약(`market`·`date`)을 지켜 목록에 같이 노출된다.
    다만 `slides: false` + `failed: true` 라서 슬라이드가 아니라 안내문으로 렌더되고,
    목록에서 '발행 실패' 배지가 붙는다.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from _rundate import run_date

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

REPO = Path(__file__).resolve().parent.parent
WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]
MARKET = {"kr": ("🇰🇷 한국장", "15:00"), "us": ("🇺🇸 미국장", "23:45")}

# 원인 코드 → (제목용 한 줄, 본문 설명)
REASONS = {
    "usage": ("Claude 사용량 한도", "한도가 소진되어 매매 판단 세션을 시작하지 못했습니다. 다음 회차는 정상 실행됩니다."),
    "manager": ("매매 결정 세션 실패", "주문서가 나오지 않아 리포트를 쓰지 않았습니다."),
    "report": ("리포트 작성 세션 실패", "매매는 기록되었을 수 있습니다 — 포트폴리오 페이지를 확인하세요."),
    "data": ("시세 수집 실패", "판단 근거가 되는 시세를 받지 못했습니다."),
    "unknown": ("자동 실행 실패", "파이프라인이 중간에 중단되었습니다."),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["kr", "us"])
    ap.add_argument("--reason", default="unknown", choices=sorted(REASONS))
    ap.add_argument("--detail", default="", help="원인 부가 정보 (예: resets 5:30am (UTC))")
    ap.add_argument("--run-url", default="", help="Actions 실행 로그 URL")
    ap.add_argument("--date", default="", help="회차 기준일 (기본: RUN_DATE)")
    a = ap.parse_args()

    day = a.date or run_date()
    label, pub = MARKET[a.mode]
    d = datetime.strptime(day, "%Y-%m-%d")
    wd = WEEKDAY[d.weekday()]
    title_reason, body_reason = REASONS[a.reason]

    out = REPO / "_posts" / f"{day}-{a.mode}-market.md"
    if out.exists():
        print(f"이미 글이 있다 — 덮어쓰지 않는다: {out.relative_to(REPO)}", file=sys.stderr)
        return 0

    detail_line = f"\n- **상세**: `{a.detail}`" if a.detail else ""
    log_line = f"\n- **실행 로그**: [{a.run_url}]({a.run_url})" if a.run_url else ""

    md = f"""---
layout: post
title: "{label} — {day} ({wd}) · 발행 실패"
date: {day} {pub}:00 +0900
categories: report
market: {a.mode}
slides: false
failed: true
---

## 이 회차는 발행되지 못했습니다

- **원인**: {title_reason}{detail_line}{log_line}

{body_reason}

**이 회차 매매는 없습니다.** 보유·현금은 직전 회차 그대로이며, 소급 체결하지 않습니다.

[포트폴리오]({{{{ '/portfolio/' | relative_url }}}}) · [채점판]({{{{ '/scoreboard/' | relative_url }}}})
"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"실패 안내글 생성: {out.relative_to(REPO)} (원인={a.reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
