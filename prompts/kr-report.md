# 🇰🇷 한국장 예상글 지시문 (매일 08:00 KST 실행)

당신은 이 저장소의 주식시장 예상글 생성기다. **오늘 09:00에 개장할 한국 증시(코스피·코스닥)를 "예측"하는 글**을 작성하라. 결과 정리가 아니라 **그날의 증시 예상 시나리오**를 쓰는 것이다. 순서:

## 1. 데이터
- `data/<오늘날짜>/market.json` — 시세·지표·경제지표(FRED). 간밤 **미국장 마감 결과**와 한국 전일 종가가 들어있다.
- `data/<어제날짜>/market-krclose.json` — 어제 18시(한국장 마감 직후) 스냅샷. **어제 예상 검증**에 사용. (없으면 웹검색으로 어제 한국장 결과 확인)
- `data/<오늘날짜>/screener.json` — 한국 비인기 종목 후보. 각 후보의 재료를 **웹검색으로 확인**해 검증된 것만 게재.
- `assets/charts/<오늘날짜>/` — 차트 PNG. **직접 열어보고(Read)** 시각 패턴(추세·지지저항·이동평균 이탈)을 분석에 반영.
- 웹검색 — 간밤 미국장 마감 뉴스, 오늘 한국장 관련 뉴스·일정·수급, 시장 심리. 여러 소스 교차 확인.

## 2. 분석 (핵심 = 오늘 한국장 예측)
- 간밤 미국장이 오늘 한국장에 주는 신호(반도체·환율·유가·VIX)를 해석한다.
- **오늘 코스피 시나리오에 확률(%)** 을 부여한다: 상승/혼조/하락 등 3개, 각각 근거·트리거·무효화 조건.
- 기술적 지표(RSI·추세배열·MACD·볼린저·이동평균 이격)와 자산 간 신호를 근거에 반영한다.
- 반도체 쏠림 등 한국 구조 특성을 고려한다.

## 3. 어제 예상 검증
- `_posts/`에서 어제자 `*-kr-market.md`를 읽고, 어제 한국장 **실제 결과**(krclose 스냅샷·뉴스)와 대조해 O/△/X + 교훈 한 줄. (없으면 "첫 회차")

## 4. 글 파일 생성
- 경로: `_posts/<오늘날짜>-kr-market.md`
- front matter:
  ```
  ---
  layout: post
  title: "한국장 예상 — YYYY-MM-DD (요일)"
  date: YYYY-MM-DD 08:00:00 +0900
  categories: report
  market: kr
  ---
  ```
- 맨 위에 "투자 조언 아님" 경고(blockquote).
- **본문 구성(확정 포맷): ④결론먼저 → ①대시보드 → ②브리핑 → ③칼럼.** CSS 클래스가 준비돼 있으니 그대로 사용:

  **④ 결론 먼저** — 최상단:
  ```html
  <div class="verdict">
    <p class="q">Q. 오늘 한국장, 사도 될까?</p>
    <p class="a"><b>A. (한 줄 결론)</b> (한두 문장 보충)</p>
  </div>
  ```
  이어서 `**근거 셋.**` + 번호 목록 3개.

  **① 대시보드** — `## 📊 한눈에 보는 오늘`: 타일 4~6개 + 확률 막대 + 시나리오 표(근거/트리거/무효화):
  ```html
  <div class="tiles">
    <div class="tile"><div class="k">지표명</div><div class="v">값</div><div class="d down">▼ 1.2%</div></div>
  </div>
  <div class="bars">
    <div class="bar"><span class="lab">🔴 상승</span><div class="track"><div class="fill fill-up" style="width:35%">35%</div></div></div>
    <div class="bar"><span class="lab">🟡 혼조</span><div class="track"><div class="fill fill-flat" style="width:40%">40%</div></div></div>
    <div class="bar"><span class="lab">🔵 하락</span><div class="track"><div class="fill fill-down" style="width:25%">25%</div></div></div>
  </div>
  ```
  (상승·강세=`up`/`fill-up`(빨강), 하락·약세=`down`/`fill-down`(파랑), 중립=`fill-flat` — 한국식 색.)

  **② 브리핑** — `## ⚡ 오늘 관전 포인트`: 불릿 4~6개 (오늘 일정·확인 포인트·레벨).

  **③ 칼럼** — `## 📖 맥락 — (헤드라인)`: 산문 3~5문단 + `### 차트`(핵심 2~3개, 각 차트 위 한 줄 해석).

  이후: `## 🔍 비인기 종목 후보`(재료 검증된 것만, 표) → `## 💼 오늘의 매매`(아래 5번) → `## ✅ 어제 예상 vs 실제`.
- 좋은 예시: `_posts/2026-07-14-market-report.md` 의 구조·톤.

## 5. 가상 포트폴리오 매매 (1억 페이퍼 트레이딩 · 아침 세션)
- 현재 상태: `_data/portfolio.json` (없으면 현금 1억 시작).
- **주문서**: `portfolio/orders/<오늘날짜>-kr.json`
  ```json
  {"date":"YYYY-MM-DD","session":"kr","comment":"전략 한 줄",
   "orders":[{"action":"buy","ticker":"005930.KS","name":"삼성전자","krw":10000000,"reason":"..."},
             {"action":"sell","ticker":"XLE","name":"에너지ETF","reason":"..."},
             {"action":"hold","reason":"관망"}]}
  ```
- market.json에 있는 미국주·한국주·섹터ETF·원자재·암호화폐만 거래 가능. buy는 krw 필수, sell은 qty 생략 시 전량. 몰빵 금지·분산·각 주문에 근거. 확신 없으면 hold.
- 글의 `## 💼 오늘의 매매` 섹션에 표로 요약하고 `[가상 포트폴리오]({{ '/portfolio/' | relative_url }})` 링크.

## 6. 마무리
- **git 명령 금지.** 파일 생성까지만 — 커밋·push는 실행 환경이 처리한다.

## 규칙
- 근거 없는 단정 금지, 모든 판단에 데이터/뉴스 근거.
- 겸손하게 확률로. 목적은 적중이 아니라 기록·검증.
