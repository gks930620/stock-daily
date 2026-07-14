# 자동화 설정 방법 (예약 실행)

이 문서는 **매일 정해진 시간에 Claude Code가 리포트를 자동 생성·게시**하도록 설정하는 방법입니다.
실행되는 명령의 내용은 [prompts/kr-report.md](../prompts/kr-report.md)·[prompts/us-report.md](../prompts/us-report.md)에 있습니다.

---

## 전체 그림

```
[정해진 시각]  스케줄러가 Claude Code 실행
   └─ 모드별 지시문(prompts/kr-report.md 등)대로:
        데이터수집(웹검색) → 분석 → _posts/오늘날짜.md 생성 → git push
[GitHub Pages]  사이트에 자동 반영 → 사용자 열람 (비용 0)
```

- **AI 실행은 하루 1번** → Claude 구독 사용량 안에서 처리 (요청당 과금 아님)
- **사용자 열람은 정적 사이트** → 몇 명이 보든 추가 비용 0

---

## 방식 A. 윈도우 작업 스케줄러 (추천)

내 PC에서 매일 정해진 시각에 Claude Code를 헤드리스로 실행합니다. git push가 로컬 인증을 그대로 쓰므로 가장 안정적입니다. (단, 그 시각에 PC가 켜져 있어야 함)

### 1) 실행 스크립트 준비
이 저장소의 `scripts/run-daily.ps1` 을 사용합니다 (아래에서 함께 생성해 둠).

### 2) 작업 스케줄러 등록

> ⚠️ **이 등록은 반드시 본인이 직접 실행하세요.** 이 예약은 매일 무인으로
> `claude -p ... --dangerously-skip-permissions`(권한 확인 없이 도구를 쓰는 자율 실행)를
> 돌립니다. 편리하지만, 신뢰하는 이 저장소 자동화 용도로만 본인 판단하에 켜세요.
> (Claude가 대신 등록하는 건 안전상 차단됩니다 — 그래서 본인이 켜는 게 맞습니다.)

**방법 ①: PowerShell 한 줄로 등록 (간단)**
PowerShell을 열고 아래를 붙여넣기:

```powershell
$repo = "C:\Users\gks93\workspace\주식시장예상클로드코드"
$action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$repo\scripts\run-daily.ps1`""
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "StockDailyReport" -Action $action -Trigger $trigger -Settings $settings -Description "매일 주식시장 리포트 (stock-daily)" -Force
```

- 확인: `Get-ScheduledTask -TaskName StockDailyReport`
- 지금 한 번 테스트 실행: `Start-ScheduledTask -TaskName StockDailyReport`
- 해제: `Unregister-ScheduledTask -TaskName StockDailyReport -Confirm:$false`

**방법 ②: 작업 스케줄러 GUI**
1. 시작 메뉴 → **작업 스케줄러** → **기본 작업 만들기**
2. 이름 `StockDailyReport` / 트리거 **매일** / 시간 `08:00`
3. 동작 **프로그램 시작** →
   - 프로그램: `powershell.exe`
   - 인수: `-ExecutionPolicy Bypass -NoProfile -File "C:\Users\gks93\workspace\주식시장예상클로드코드\scripts\run-daily.ps1"`
4. 완료

---

## 방식 B. Claude Code 예약 작업(routine) — 클라우드

PC를 안 켜도 됩니다. Claude Code 대화창에서:

```
/schedule
```

를 실행해 매일 cron 예약을 만들고, 실행 내용으로 [prompts/kr-report.md](../prompts/kr-report.md)·[prompts/us-report.md](../prompts/us-report.md)의 지시문을 넣습니다.

⚠️ **주의**: 클라우드에서 실행되므로 이 저장소에 **git push 할 수 있는 권한(깃허브 인증)** 이 그 환경에 필요합니다. 로컬 파일/차트 생성이 필요 없는 "웹검색 기반 리포트"에는 적합하지만, push 인증 설정이 방식 A보다 까다롭습니다. 처음엔 **방식 A를 권장**합니다.

---

## 실행 시각 추천

| 목적 | 추천 시각(KST) | 이유 |
|---|---|---|
| 미국장 마감 반영 + 한국장 개장 전 브리핑 | **오전 8:00** | 밤사이 미국 결과 + 오늘 한국장 준비 |
| (선택) 한국장 마감 정리 | 오후 4:00 | 국내 마감 시황 |

우선 **오전 8:00 하루 1회**로 시작하는 것을 권장합니다.

---

## 2단계 확장 (나중에)

- **Python 설치 후** `scripts/`에 `yfinance` 데이터 수집 + 차트(PNG) 생성 스크립트를 추가하면, 리포트에 실제 차트가 들어갑니다.
- 그때 지시문의 데이터 수집 단계에 "파이썬 스크립트 실행 → 차트 생성"이 추가됩니다.
