# 로컬 자동화 (윈도우 작업 스케줄러 · 백업용)

> ⭐ **기본 자동화는 클라우드([CLOUD-AUTOMATION.md](CLOUD-AUTOMATION.md))입니다.** 이 문서는 내 PC에서 돌리는 **백업 방식**입니다.
> 둘 다 켜면 중복 실행되니 하나만 사용하세요.

매일 정해진 시간에 내 PC에서 Claude Code가 예상글을 자동 생성·게시하도록 설정하는 방법입니다.
실행 지시문: [prompts/kr-report.md](../prompts/kr-report.md)·[prompts/us-report.md](../prompts/us-report.md)

---

## 전체 그림

```
[정해진 시각]  스케줄러가 run-daily.ps1 [모드] 실행
   kr(14:30) = 수집+차트+스크리너 → 매니저 3인 매매 → 종합 리포트(~14:45) → 체결 → push
   us(23:30) = 수집+차트 → 매니저 3인 매매 → 종합 리포트(~23:45) → 체결 → push
[GitHub Pages]  사이트에 자동 반영 → 사용자 열람 (비용 0)
```

- **AI 실행은 하루 2회(kr·us) × 회차당 4세션** (매니저 3 + 애널리스트 1, 전원 xhigh) → Max 구독 사용량으로 처리 (요청당 과금 아님, 모델: 최신 opus)
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
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# 2개 작업 등록: 14:30 kr / 23:30 us (장중)
@(
  @{Name="StockDaily-KR"; Time="2:30pm";  Mode="kr"},
  @{Name="StockDaily-US"; Time="11:30pm"; Mode="us"}
) | ForEach-Object {
  $action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$repo\scripts\run-daily.ps1`" $($_.Mode)"
  $trigger = New-ScheduledTaskTrigger -Daily -At $_.Time
  Register-ScheduledTask -TaskName $_.Name -Action $action -Trigger $trigger -Settings $settings -Description "stock-daily $($_.Mode)" -Force
}
```

- 확인: `Get-ScheduledTask -TaskName StockDaily-*`
- 지금 한 번 테스트: `Start-ScheduledTask -TaskName StockDaily-KR`
- 해제: `Get-ScheduledTask -TaskName StockDaily-* | Unregister-ScheduledTask -Confirm:$false`
- (과거 작업 `StockDailyReport`·`StockDaily-Collect`가 남아있으면 함께 삭제)

**방법 ②: 작업 스케줄러 GUI** — 위 2개 작업을 각각 [기본 작업 만들기]로 등록 (인수 끝에 모드 `kr`/`us`를 붙이는 것만 주의)

---

## 방식 B. Claude Code 예약 작업(routine) — 클라우드

PC를 안 켜도 됩니다. Claude Code 대화창에서:

```
/schedule
```

를 실행해 매일 cron 예약을 만들고, 실행 내용으로 [prompts/kr-report.md](../prompts/kr-report.md)·[prompts/us-report.md](../prompts/us-report.md)의 지시문을 넣습니다.

⚠️ **주의**: 클라우드에서 실행되므로 이 저장소에 **git push 할 수 있는 권한(깃허브 인증)** 이 그 환경에 필요합니다. 로컬 파일/차트 생성이 필요 없는 "웹검색 기반 리포트"에는 적합하지만, push 인증 설정이 방식 A보다 까다롭습니다. 처음엔 **방식 A를 권장**합니다.

---

## 실행 시각 (확정)

| 시각(KST) | 모드 | 내용 |
|---|---|---|
| 14:30 | `kr` | 🇰🇷 장중 분석 → 14:45 리포트 + 그 시세로 매매 |
| 23:30 | `us` | 🇺🇸 장중 분석 → 23:45 리포트 + 그 시세로 매매 |

---

## 참고

- 상세 규칙(포맷·체결·데이터 함정): [RULES.md](RULES.md)
- 클라우드 방식(권장): [CLOUD-AUTOMATION.md](CLOUD-AUTOMATION.md)
