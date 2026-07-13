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
config/watchlist.yaml           # 수집 종목 목록 (여기만 편집하면 반영)
scripts/collect_data.py         # 시세 데이터 수집 (yfinance)
scripts/run-daily.ps1           # 예약 실행 스크립트 (수집→분석→push)
requirements.txt                # 파이썬 패키지 목록
AUTOMATION.md                   # 예약(루틴) 설정 방법
TOOLING.md                      # 파이썬/venv 도구 설정
DESIGN.md                       # 전체 설계 문서
```

## 동작 흐름

```
스케줄러(오전 8시)
  → (1) 파이썬(scripts/collect_data.py)이 시세·지표 수집 → data/오늘/market.json
  → (2) Claude Code가 그 데이터 + 웹검색(뉴스)으로 분석 → _posts/오늘.md 생성 → git push
GitHub Pages → 사이트 자동 반영
```

- **숫자 데이터**(약 45종목: 지수·섹터ETF·원자재·암호화폐·채권금리·환율·주요주 + MACD·볼린저·추세배열 등 지표)는 Python(yfinance)이 안정적으로 수집
- 수집 종목은 [config/watchlist.yaml](config/watchlist.yaml)에서 자유롭게 추가/삭제
- **뉴스·시황**은 Claude 웹검색으로 여러 소스 커버
- 파이썬 환경 설정은 [TOOLING.md](TOOLING.md) 참고

## 자동화 켜기

[AUTOMATION.md](AUTOMATION.md) 참고. 처음엔 **윈도우 작업 스케줄러(방식 A)** 로 오전 8시 1회 실행을 권장합니다.

## 단계

- **1단계 (현재)**: Python 시세 수집(지수·환율·금리·지표) + 웹검색 뉴스 → 리포트
- **2단계 (예정)**: 수집 데이터로 차트(PNG) 생성해 리포트에 삽입
- **3단계 (선택)**: 한국 상세수급(pykrx)·경제지표(FRED)·특정 사이트 크롤러 확장

> ⚠️ 투자 조언이 아닙니다. 매매 판단과 책임은 본인에게 있습니다.
