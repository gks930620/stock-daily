# 로컬 실행 스크립트 (백업용 — 기본 자동화는 GitHub Actions .github/workflows/daily.yml)
# 사용: .\run-daily.ps1 [kr|collect|us]
#   kr(기본)  = 수집 + 🇰🇷 한국장 예상글 + 매매   (아침 08시용)
#   collect   = 수집만 (한국장 마감 스냅샷, 18시용)
#   us        = 수집 + 🇺🇸 미국장 예상글 + 매매   (저녁 21시용)
param([ValidateSet("kr","collect","us")][string]$Mode = "kr")

$repo = "C:\Users\gks93\workspace\주식시장예상클로드코드"
$venvPython = "$repo\.venv\Scripts\python.exe"
$claude = "C:\Users\gks93\AppData\Roaming\npm\claude.cmd"
Set-Location $repo

$logDir = "$repo\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
try { Start-Transcript -Path "$logDir\last-run.log" -Force | Out-Null } catch {}

$label = @{ kr = "morning"; collect = "krclose"; us = "uspre" }[$Mode]
Write-Host "===== 시작($Mode): $(Get-Date) ====="

try {
    git pull --rebase --autostash
    if ($LASTEXITCODE -ne 0) { Write-Warning "git pull 실패(무시하고 계속)" }
} catch { Write-Warning "git pull 예외(무시하고 계속): $_" }

Write-Host "[1] 시세·경제지표 수집 ($label)..."
& $venvPython "$repo\scripts\collect_data.py" $label
if ($LASTEXITCODE -ne 0) { Write-Warning "데이터 수집 일부 실패(계속 진행)" }

if ($Mode -ne "collect") {
    Write-Host "[2] 차트 생성..."
    & $venvPython "$repo\scripts\make_charts.py"
    if ($LASTEXITCODE -ne 0) { Write-Warning "차트 생성 실패(계속 진행)" }

    if ($Mode -eq "kr") {
        Write-Host "[3] 비인기 종목 스크리닝..."
        & $venvPython "$repo\scripts\screener.py"
        if ($LASTEXITCODE -ne 0) { Write-Warning "스크리너 실패(계속 진행)" }
    }

    Write-Host "[4] Claude 분석·예상글 생성 ($Mode, 최신 opus)..."
    $prompt = Get-Content -Raw "$repo\prompts\$Mode-report.md"
    & $claude -p $prompt --model opus --dangerously-skip-permissions

    Write-Host "[5] 포트폴리오 매매 반영..."
    & $venvPython "$repo\scripts\portfolio.py"
    if ($LASTEXITCODE -ne 0) { Write-Warning "포트폴리오 갱신 실패(계속 진행)" }
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
