# 매일 주식시장 예상 (stock-daily)

**GitHub 서버**가 평일 2회 **장중에** 데이터를 모으고 **Claude가 분석**해, **"지금 이 종목 사라/팔아라"** 리포트를 공개 사이트에 자동 게시합니다. 리포트를 본 사람이 **30분 안에 같은 가격대로 살 수 있는 시각**에 내며, 성향이 다른 **AI 3인이 각자 1억으로 실제 매매**해 누가 잘하는지 추적합니다.

- 🌐 **공개 사이트**: https://gks930620.github.io/stock-daily/
- ⏰ 평일 2회 장중 자동 실행 (GitHub Actions): **🇰🇷 14:45 발행**(마감 15:30 전 매수 가능) · **🇺🇸 23:45 발행**(장중)
- 💼 **가상 1억 페이퍼 트레이딩** — 예상에 따라 실제로 매매하고 성과를 추적 ([포트폴리오](https://gks930620.github.io/stock-daily/portfolio/))
- ⚠️ 투자 조언이 아닙니다. "예측 적중"이 아니라 **근거 있는 확률 + 자기검증** 기록입니다.

## 📚 문서 지도

| 문서 | 내용 |
|---|---|
| **[docs/OVERVIEW.md](docs/OVERVIEW.md)** | ⭐ **여기부터** — 프로젝트·자동화를 그림(흐름도)으로 한눈에 |
| [docs/RULES.md](docs/RULES.md) | ⭐ **운영 규칙서** — 포맷·체결규칙·데이터 함정·재발방지 체크 |
| [docs/DESIGN.md](docs/DESIGN.md) | 전체 설계 (철학·데이터소스·리포트 구조·스크리너 로직·로드맵) |
| [docs/CLOUD-AUTOMATION.md](docs/CLOUD-AUTOMATION.md) | ⭐ 클라우드 자동화 (GitHub Actions, Max 사용량, 토큰 발급) |
| [docs/AUTOMATION.md](docs/AUTOMATION.md) | 로컬 자동화 (윈도우 작업 스케줄러 · 백업용) |
| [docs/TOOLING.md](docs/TOOLING.md) | 파이썬/venv 환경 설정 |

## 🗂 폴더 구조

```
_config.yml / index.md            Jekyll 사이트 설정 / 홈
_posts/YYYY-MM-DD-kr-market.md    🇰🇷 한국장 리포트 (평일 14:45 발행)
_posts/YYYY-MM-DD-us-market.md    🇺🇸 미국장 리포트 (평일 23:45 발행)
portfolio.md / portfolio-<성향>.md   3인 비교 허브 / 성향별 상세 페이지
_data/portfolio-<성향>.json        성향별 계좌 상태 (stable·aggressive·contrarian)
portfolio/orders/<날짜>-<kr|us>-<성향>.json  세션·성향별 매매 주문서 (AI 결정)
assets/charts/ · assets/portfolio/   차트 PNG · 성향별 자산곡선
data/YYYY-MM-DD/market*.json      시세 스냅샷 (kr/us — 검증용 커밋)
config/watchlist.yaml             수집 종목 목록 (여기만 편집하면 반영)
prompts/kr-report.md · us-report.md  세션별 종합 리포트 지시문 (애널리스트)
prompts/portfolio.md · persona-*.md  매매 공용 규칙 · 성향별 지시문 (매니저 3인)
scripts/collect_data.py           시세+경제지표(FRED) 수집
scripts/make_charts.py            차트 이미지 생성
scripts/screener.py               비인기 종목 후보 발굴 (한국)
scripts/portfolio.py              가상 1억 체결·평가·자산곡선
scripts/run-daily.ps1             로컬 실행 스크립트 (kr|collect|us)
.github/workflows/daily.yml       클라우드 자동 실행 (GitHub Actions, 평일 2회 장중)
docs/                             설계·규칙·문서
```

## ⚙️ 자동화 켜기

**클라우드(권장)** — 내 PC 없이 GitHub 서버에서 실행: [docs/CLOUD-AUTOMATION.md](docs/CLOUD-AUTOMATION.md)
1. `claude setup-token` 으로 토큰 발급
2. GitHub Secret `CLAUDE_CODE_OAUTH_TOKEN` 등록

이후 평일 2회 자동으로 [수집 → 차트 → (스크리너) → **AI 3인 매매 결정** → **애널리스트 종합 리포트** → 체결 → 게시]가 돌아갑니다.
