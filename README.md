# 매일 주식시장 예상 (Claude Code 자동 리포트)

매일 아침 Claude Code가 미국·한국 시장의 데이터·뉴스를 종합해 **확률적 시장 시나리오 리포트**를 만들고, GitHub Pages 공개 사이트에 자동 게시합니다.

- **분석**: Claude Code (하루 1회, 구독 사용량 내)
- **게시**: 마크다운(.md) → GitHub Pages(Jekyll) 정적 사이트 → 사용자 열람 비용 0
- **목적**: "예측 적중"이 아니라 근거 있는 판단 + 자기검증 기록

## 구조

```
_config.yml                     # Jekyll 사이트 설정
index.md                        # 홈 (리포트 목록 자동 표시)
_posts/YYYY-MM-DD-market-report.md   # 매일 생성되는 리포트
prompts/daily-report.md         # 매일 실행되는 지시문(Claude에게)
scripts/run-daily.ps1           # 예약 실행 스크립트
AUTOMATION.md                   # 예약(루틴) 설정 방법
DESIGN.md                       # 전체 설계 문서
```

## 동작 흐름

```
스케줄러(오전 8시) → Claude Code 실행
  → 웹검색으로 데이터 수집 → 분석 → _posts/오늘.md 생성 → git push
GitHub Pages → 사이트 자동 반영
```

## 자동화 켜기

[AUTOMATION.md](AUTOMATION.md) 참고. 처음엔 **윈도우 작업 스케줄러(방식 A)** 로 오전 8시 1회 실행을 권장합니다.

## 단계

- **1단계 (현재)**: 웹검색 기반 뉴스·시황 리포트 (Python 불필요)
- **2단계 (예정)**: Python `yfinance`로 차트·지표 추가

> ⚠️ 투자 조언이 아닙니다. 매매 판단과 책임은 본인에게 있습니다.
