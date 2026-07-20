# 로컬 실행 스크립트 (백업용 — 기본 자동화는 GitHub Actions .github/workflows/daily.yml)
# 사용: .\run-daily.ps1 [kr|us]   ← 장이 열려 있는 동안 실행
#   kr(기본) = 🇰🇷 14시 시작 → ~15:00 리포트·체결 (독자는 15:00~15:30 마감 전 매수 가능)
#   us       = 🇺🇸 22:40 시작 → ~23:40 리포트·체결 (장중이라 바로 매수 가능)
# 체결가는 AI 판단이 끝난 뒤 "다시 수집한" 시장가 → AI가 못 본 가격 + 독자가 실제 살 수 있는 가격
param([ValidateSet("kr","us")][string]$Mode = "kr")

$repo = "C:\Users\gks93\workspace\주식시장예상클로드코드"
$venvPython = "$repo\.venv\Scripts\python.exe"
$claude = "C:\Users\gks93\AppData\Roaming\npm\claude.cmd"
Set-Location $repo

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

    $today = Get-Date -Format "yyyy-MM-dd"

    # ① 성향별 포트폴리오 매니저 3인이 먼저 종목을 확정 (각자 독립 세션·독립 계좌) — effort xhigh
    foreach ($P in @("stable","aggressive","contrarian")) {
        Write-Host "[4] Claude(①포트폴리오 매니저·$P) 매매 결정 ($Mode)..."
        $pfPrompt = (Get-Content -Raw "$repo\prompts\persona-$P.md") + "`n" + (Get-Content -Raw "$repo\prompts\portfolio.md") + @"

[실행 안내]
- 오늘 날짜(KST): $today
- 이번 세션: $Mode / 너의 성향 id: $P
- 주문서 파일명은 반드시 portfolio/orders/$today-$Mode-$P.json
- 네 계좌 파일: _data/portfolio-$P.json (없으면 현금 1억 시작)
- 너는 1차 결정자다. 데이터를 직접 보고 종목을 정하라 (애널리스트 리포트는 아직 없다).
- git 금지. 주문서 JSON 생성까지만.
"@
        & $claude -p $pfPrompt --model opus --effort xhigh --dangerously-skip-permissions
    }

    # ② 애널리스트가 3인 주문서를 종합해 '오늘의 매수/매도 종목' 리포트 작성 — effort xhigh
    Write-Host "[5] Claude(②애널리스트) 3인 종합 리포트 ($Mode)..."
    $nowHM = Get-Date -Format "HH:mm"
    $prompt = (Get-Content -Raw "$repo\prompts\$Mode-report.md") + @"

[실행 안내]
- 오늘 날짜(KST): $today
- 지금 시각(KST): $nowHM → front matter의 date를 반드시 "$today ${nowHM}:00 +0900" 로 쓸 것 (실제 작성 시각).
- 방금 3인이 낸 주문서 portfolio/orders/$today-$Mode-{stable,aggressive,contrarian}.json 를 반드시 읽어 종합하라.
- git 금지. 글 파일 생성까지만.
"@
    & $claude -p $prompt --model opus --effort xhigh --dangerously-skip-permissions

}

# 체결가 = AI가 분석한 그 시세. 가격을 보고 판단했으니 그 가격에 산다.
foreach ($P in @("stable","aggressive","contrarian")) {
    Write-Host "[포트폴리오·$P] 체결·평가 ($label)..."
    & $venvPython "$repo\scripts\portfolio.py" $label $P
    if ($LASTEXITCODE -ne 0) { Write-Warning "포트폴리오($P) 갱신 실패(계속 진행)" }
}

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
