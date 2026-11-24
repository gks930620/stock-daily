---
name: kr-report-timing-gotcha
description: KR 장중 리포트의 기준가/타이밍 처리 — 데이터는 장 마감 후 생성됨
metadata:
  type: project
---

한국장 리포트(`_posts/<date>-kr-market.md`)는 지시문상 "장중 15:00~15:30 매수" 프레임이지만, 실제 `data/<date>/market.json`의 `generated_at_kst`는 **장 마감(15:30) 이후**(예: 2026-11-24는 21:12)다. 따라서 KR 종목 시세는 사실상 **당일 종가 스냅샷**이다.

**Why:** 장중인 척 쓰되 기준가가 실은 종가라, 이를 숨기면 부정확해진다.

**How to apply:** `기준가 = <date> 종가 스냅샷`으로 명시하고 독자에게 "다음 거래일 시장가로 비교"라고 안내. 또한 美 지수·엔비디아 등은 `data_date`가 보통 전일(간밤 뉴욕)이니 KR(당일)과 날짜가 다름을 details 데이터 유의 박스에 적어라. 슬라이드는 마침표 0~2개(구절로만), 평범형 2인은 반복 시행이라 표를 2로 세지 말 것. 채점은 절대손익이 아니라 scoreboard의 `excess_pct`/`vs_bench`로.
