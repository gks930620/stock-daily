# 매일 주식시장 예상 (stock-daily)

매일 아침 **GitHub 서버**가 데이터를 모으고 **Claude가 분석**해, 확률적 시장 시나리오 리포트를 공개 사이트에 자동 게시합니다.

- 🌐 **공개 사이트**: https://gks930620.github.io/stock-daily/
- ⏰ 하루 3회 자동 실행 (GitHub Actions): **08시 🇰🇷 한국장 예상글** · 18시 수집(한국장 마감) · **21시 🇺🇸 미국장 예상글**
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
_config.yml / index.md          Jekyll 사이트 설정 / 홈
_posts/YYYY-MM-DD-...md          매일 생성되는 리포트
assets/charts/YYYY-MM-DD/*.png   리포트에 삽입되는 차트
config/watchlist.yaml            수집 종목 목록 (여기만 편집하면 반영)
prompts/kr-report.md             🇰🇷 한국장 예상글 지시문 (08시)
prompts/us-report.md             🇺🇸 미국장 예상글 지시문 (21시)
scripts/collect_data.py          시세+경제지표(FRED) 수집
scripts/make_charts.py           차트 이미지 생성
scripts/screener.py              비인기 종목 후보 발굴
scripts/run-daily.ps1            로컬 실행 스크립트
.github/workflows/daily.yml      클라우드 자동 실행 (GitHub Actions)
docs/                            설계·문서
```

## ⚙️ 자동화 켜기

**클라우드(권장)** — 내 PC 없이 GitHub 서버에서 실행: [docs/CLOUD-AUTOMATION.md](docs/CLOUD-AUTOMATION.md)
1. `claude setup-token` 으로 토큰 발급
2. GitHub Secret `CLAUDE_CODE_OAUTH_TOKEN` 등록

이후 매일 자동으로 [수집 → 차트 → 스크리너 → Claude 분석 → 게시]가 돌아갑니다.
