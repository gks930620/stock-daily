# 매일 주식시장 예상 (stock-daily)

**GitHub 서버**가 평일 2회 **장중에** 데이터를 모으고 **Claude가 분석**해, **"지금 이 종목 사라/팔아라"** 리포트를 공개 사이트에 자동 게시합니다. 리포트를 본 사람이 **30분 안에 같은 가격대로 살 수 있는 시각**에 내며, **AI 4인이 각자 1억으로 실제 매매**해 누가 잘하는지 추적합니다 (🛡️안정·🚀공격[opus] + 동일 지시문 대조군 🙂평범형 2인[fable]).

- 🌐 **공개 사이트**: https://gks930620.github.io/stock-daily/
- ⏰ 평일 2회 장중 자동 실행 (GitHub Actions): **🇰🇷 15:00 발행**(마감 15:30 전 매수 가능) · **🇺🇸 23:45 발행**(장중)
- 💼 **가상 1억 페이퍼 트레이딩** — 예상에 따라 실제로 매매하고 성과를 추적 ([포트폴리오](https://gks930620.github.io/stock-daily/portfolio/))
- 🧮 **AI 채점판** — "진짜 잘하는가"를 종목 콜 단위 초과수익으로 판정 ([채점판](https://gks930620.github.io/stock-daily/scoreboard/)). 계좌 수익률은 하루 1표본이라 실력/운 구분이 안 되므로, 모든 종목 콜을 벤치마크 대비로 소급 채점합니다
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
| [디자인_Halo/halo-design-kit/](디자인_Halo/halo-design-kit/) | 🎨 **디자인 시스템 Halo** — 원칙·토큰·컴포넌트 |

## 🎨 디자인: Halo

**단일 출처는 `assets/css/halo-tokens.css` 의 `:root` 토큰.** 새 컴포넌트는 토큰만 조합해 만들고
색·그림자·둥글기를 하드코딩하지 않는다 — 하는 순간 다크 모드가 그 부분만 깨진다.

- 원칙 4개 (`디자인_Halo/halo-design-kit/HALO-디자인-가이드.md`):
  ① 읽는 면(카드·본문)은 불투명 · ② 그라디언트는 초점에만 · ③ 유리(blur)는 헤더만 · ④ 카드 윗변 1px 그라디언트 선
- 다크 모드: `<html data-theme>` 방식. 헤더 우측 토글, `localStorage` 저장, FOUC 방지 인라인 스크립트
- **이 프로젝트만의 예외 2가지**
  - **시장 등락색은 빨강/파랑을 유지**한다(`--up`/`--down`). 한국식 관례이고 브랜드색이 아니라 **데이터 의미색**이라, Halo 팔레트로 바꾸면 숫자의 뜻이 사라진다
  - **본문 16.5px** (킷 기본 14.5px). 이 사이트는 앱 UI가 아니라 **읽는 물건**이다

## 🗂 폴더 구조

```
_config.yml / index.md            Jekyll 사이트 설정 / 홈
_posts/YYYY-MM-DD-kr-market.md    🇰🇷 한국장 리포트 (평일 15:00 발행)
_posts/YYYY-MM-DD-us-market.md    🇺🇸 미국장 리포트 (평일 23:45 발행)
portfolio.md / portfolio-<id>.md     4인 비교 허브 / 계좌별 상세 페이지
_data/portfolio-<성향>.json        계좌 상태 (stable·aggressive·normal1·normal2)
portfolio/orders/<날짜>-<kr|us>-<성향>.json  세션·성향별 매매 주문서 (AI 결정)
assets/charts/ · assets/portfolio/   차트 PNG · 성향별 자산곡선
data/YYYY-MM-DD/market*.json      시세 스냅샷 (kr/us — 검증용 커밋)
config/watchlist.yaml             수집 종목 목록 (여기만 편집하면 반영)
prompts/kr-report.md · us-report.md  세션별 종합 리포트 지시문 (애널리스트)
prompts/portfolio.md · persona-*.md  매매 공용 규칙 · 매니저 4인 지시문
scripts/collect_data.py           시세+경제지표(FRED) 수집
scripts/make_charts.py            차트 이미지 생성
scripts/screener.py               비인기 종목 후보 발굴 (한국)
scripts/portfolio.py              가상 1억 체결·평가·자산곡선
scripts/holding_charts.py         보유 종목별 일별 추이 그래프 (매수 시점 표기)
scripts/_rundate.py               회차 기준일(RUN_DATE) — 전 단계가 같은 하루를 보게 하는 기준
scripts/verify_run.py             커밋 전 산출물 점검 (리포트·주문서 4인·체결 4인)
scripts/fallback_post.py          회차 실패 시 '발행 실패' 안내글 생성 (AI 아닌 코드가 씀)
strategies/ · backtest.py         🤖 알고리즘 전략 도구 — **보류 중**, 파이프라인 미연결 (RULES §0-3)
scripts/scoreboard.py             🧮 AI 채점판 — 종목 콜 단위 소급 채점 (/scoreboard/)

scripts/run-daily.ps1             로컬 실행 스크립트 (kr|us)
.github/workflows/daily.yml       클라우드 자동 실행 (GitHub Actions, 평일 2회 장중)
docs/                             설계·규칙·문서
```

## ⚙️ 자동화 켜기

**클라우드(권장)** — 내 PC 없이 GitHub 서버에서 실행: [docs/CLOUD-AUTOMATION.md](docs/CLOUD-AUTOMATION.md)
1. `claude setup-token` 으로 토큰 발급
2. GitHub Secret `CLAUDE_CODE_OAUTH_TOKEN` 등록

이후 평일 2회 자동으로 [수집 → 차트 → (스크리너) → **AI 4인 매매 결정** → **애널리스트 종합 리포트** → 체결 → 게시]가 돌아갑니다.
