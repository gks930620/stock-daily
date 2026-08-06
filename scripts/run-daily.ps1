# 로컬 실행 스크립트 (백업용 — 기본 자동화는 GitHub Actions .github/workflows/daily.yml)
# 사용: .\run-daily.ps1 [kr|us]   ← 장이 열려 있는 동안 실행
#   kr(기본) = 🇰🇷 14:40 시작 → ~15:00 리포트·체결 (독자는 15:30 마감 전 매수 가능)
#   us       = 🇺🇸 23:30 시작 → ~23:45 리포트·체결 (장중이라 바로 매수 가능)
# 체결가 = AI가 분석한 그 시세(market.json) — 가격을 보고 판단했으니 그 가격에 산다
param([ValidateSet("kr","us")][string]$Mode = "kr")

# 저장소 경로는 **이 스크립트 위치에서 유도**한다 (하드코딩하면 폴더를 옮기는 순간 죽는다 —
# 실제로 예전 경로 '주식시장예상클로드코드'가 남아 있어 로컬 백업 실행이 동작하지 않았다).
$repo = Split-Path -Parent $PSScriptRoot
$venvPython = "$repo\.venv\Scripts\python.exe"
$claude = "C:\Users\gks93\AppData\Roaming\npm\claude.cmd"
if (-not (Test-Path $venvPython)) { throw "가상환경 없음: $venvPython (docs/TOOLING.md 참조)" }
if (-not (Test-Path $claude))     { throw "claude CLI 없음: $claude" }
Set-Location $repo

# 회차 기준일 — 파이프라인 전 단계가 같은 하루를 보게 고정한다 (자정 넘김 대비, scripts/_rundate.py)
$env:RUN_DATE = Get-Date -Format "yyyy-MM-dd"

$logDir = "$repo\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
try { Start-Transcript -Path "$logDir\last-run.log" -Force | Out-Null } catch {}

$label = $Mode
Write-Host "===== 시작($Mode): $(Get-Date) ====="

try {
    git pull --rebase --autostash
    if ($LASTEXITCODE -ne 0) { Write-Warning "git pull 실패(무시하고 계속)" }
} catch { Write-Warning "git pull 예외(무시하고 계속): $_" }

Write-Host "[1] 시세·경제지표 수집 ($label)..."
& $venvPython "$repo\scripts\collect_data.py" $label
if ($LASTEXITCODE -ne 0) { Write-Warning "데이터 수집 일부 실패(계속 진행)" }

if ($true) {
    Write-Host "[2] 차트 생성..."
    & $venvPython "$repo\scripts\make_charts.py"
    if ($LASTEXITCODE -ne 0) { Write-Warning "차트 생성 실패(계속 진행)" }

    if ($Mode -eq "kr") {
        Write-Host "[3] 비인기 종목 스크리닝..."
        & $venvPython "$repo\scripts\screener.py"
        if ($LASTEXITCODE -ne 0) { Write-Warning "스크리너 실패(계속 진행)" }
    }

    $today = $env:RUN_DATE

    # ① 포트폴리오 매니저 4인이 먼저 종목을 확정 (각자 독립 세션·독립 계좌) — effort xhigh
    #    성향파 2명(안정·공격, opus) + 평범형 2명(동일 지시문 대조군, fable)
    #    ⚠️ 모델을 성향별로 나눠야 한다 — 전원 opus로 돌리면 평범형 대조군의 조건(fable)이 달라져
    #       클라우드 실행과 결과를 나란히 비교할 수 없다. daily.yml과 반드시 일치시킬 것.
    foreach ($P in @("stable","aggressive","normal1","normal2")) {
        $model = if ($P -like "normal*") { "fable" } else { "opus" }
        Write-Host "[4] Claude(①포트폴리오 매니저·$P · 모델 $model) 매매 결정 ($Mode)..."
        $pfPrompt = (Get-Content -Raw "$repo\prompts\persona-$P.md") + "`n" + (Get-Content -Raw "$repo\prompts\portfolio.md") + @"

[실행 안내]
- 오늘 날짜(KST): $today
- 이번 세션: $Mode / 너의 성향 id: $P
- 주문서 파일명은 반드시 portfolio/orders/$today-$Mode-$P.json
- 네 계좌 파일: _data/portfolio-$P.json (없으면 현금 1억 시작)
- 너는 1차 결정자다. 데이터를 직접 보고 종목을 정하라 (애널리스트 리포트는 아직 없다).
- git 금지. 주문서 JSON 생성까지만.
"@
        & $claude -p $pfPrompt --model $model --effort xhigh --dangerously-skip-permissions
    }

    # ② 애널리스트가 4인 주문서를 종합해 '오늘의 매수/매도 종목' 리포트 작성 — effort xhigh
    Write-Host "[5] Claude(②애널리스트) 4인 종합 리포트 ($Mode)..."
    # 자정을 넘겼으면 회차 마지막 순간(23:59)으로 고정 — 글 파일명은 RUN_DATE 기준이라
    # front matter만 다음 날로 튀면 목록·URL이 어긋난다.
    $nowHM = if ((Get-Date -Format "yyyy-MM-dd") -eq $today) { Get-Date -Format "HH:mm" } else { "23:59" }
    $prompt = (Get-Content -Raw "$repo\prompts\$Mode-report.md") + @"

[실행 안내]
- 오늘 날짜(KST): $today
- 지금 시각(KST): $nowHM → front matter의 date를 반드시 "$today ${nowHM}:00 +0900" 로 쓸 것 (실제 작성 시각).
- 방금 4인이 낸 주문서 portfolio/orders/$today-$Mode-{stable,aggressive,normal1,normal2}.json 를 반드시 읽어 종합하라.
- git 금지. 글 파일 생성까지만.
"@
    & $claude -p $prompt --model opus --effort xhigh --dangerously-skip-permissions

}

# 체결가 = AI가 분석한 그 시세. 가격을 보고 판단했으니 그 가격에 산다.
foreach ($P in @("stable","aggressive","normal1","normal2")) {
    Write-Host "[포트폴리오·$P] 체결·평가 ($label)..."
    & $venvPython "$repo\scripts\portfolio.py" $label $P
    if ($LASTEXITCODE -ne 0) { Write-Warning "포트폴리오($P) 갱신 실패(계속 진행)" }
}

# 🤖 알고리즘 계좌 — 코드가 규칙대로 판단 (strategies/). AI 4인과 같은 시세·같은 체결 규칙.
#    ⚠️ 전략 추가는 backtest.py 검증구간 통과가 조건 (docs/RULES.md §0-3)
foreach ($A in @("bench")) {
    Write-Host "[알고리즘·$A] 전략 실행 → 체결 ($label)..."
    & $venvPython "$repo\scripts\run_strategy.py" $A $label $A
    if ($LASTEXITCODE -ne 0) { Write-Warning "전략($A) 실행 실패(계속 진행)" }
    & $venvPython "$repo\scripts\portfolio.py" $label $A
    if ($LASTEXITCODE -ne 0) { Write-Warning "알고리즘 계좌($A) 갱신 실패(계속 진행)" }
}

# 보유 종목별 '일별 추이 + 내 매수 시점' 그래프 — 4계좌 전부 돌린 뒤 한 번만
Write-Host "[보유종목 차트] 생성..."
& $venvPython "$repo\scripts\holding_charts.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "보유종목 차트 실패(계속 진행)" }

# 🧮 AI 채점판 — 종목 콜 단위 소급 채점 (계좌 수익률만으론 실력/운 구분 불가)
Write-Host "[채점판] 갱신..."
& $venvPython "$repo\scripts\scoreboard.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "채점판 실패(계속 진행)" }

# 커밋 전 관문 — 리포트·주문서 4인·체결 4인이 다 맞아야 게시한다 (조용한 실패 금지)
Write-Host "[점검] 회차 산출물 확인..."
& $venvPython "$repo\scripts\verify_run.py" $Mode
if ($LASTEXITCODE -ne 0) { throw "회차 점검 실패 — 게시 중단. 위 오류를 확인하세요." }

Write-Host "커밋·푸시..."
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  git commit -m "auto($Mode): $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
  git push
} else {
  Write-Host "변경 없음 — 커밋 생략"
}

Write-Host "===== 완료: $(Get-Date) ====="
try { Stop-Transcript | Out-Null } catch {}
