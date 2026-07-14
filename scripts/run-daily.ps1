# 매일 실행 스크립트 — 작업 스케줄러가 이 파일을 호출합니다.
# 순서: 저장소 이동 → (1) 시세·경제지표 수집 → (2) 차트 생성 → (3) 스크리너 → (4) Claude 분석·리포트·push
#
# 주의: $ErrorActionPreference를 Stop으로 두지 않습니다.
#   PowerShell 5.1에서 git 같은 네이티브 명령의 stderr 출력이 Stop과 만나면
#   정상 실행도 실패로 처리되어 스크립트가 중단되기 때문입니다.

# 이 저장소 경로 / 프로젝트 전용 파이썬(venv) / claude CLI 경로
$repo = "C:\Users\gks93\workspace\주식시장예상클로드코드"
$venvPython = "$repo\.venv\Scripts\python.exe"
$claude = "C:\Users\gks93\AppData\Roaming\npm\claude.cmd"
Set-Location $repo

# 실행 로그 (실패 시 원인 확인용) — logs\last-run.log 에 기록
$logDir = "$repo\logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
try { Start-Transcript -Path "$logDir\last-run.log" -Force | Out-Null } catch {}

Write-Host "===== 시작: $(Get-Date) ====="

# 최신 상태로 동기화 (실패해도 계속 진행. --autostash로 로컬 변경 자동 보관)
try {
    git pull --rebase --autostash
    if ($LASTEXITCODE -ne 0) { Write-Warning "git pull 실패(무시하고 계속)" }
} catch {
    Write-Warning "git pull 예외(무시하고 계속): $_"
}

# (1) 시세·경제지표 수집 → data\<오늘날짜>\market.json
Write-Host "[1/4] 시세·경제지표 수집..."
& $venvPython "$repo\scripts\collect_data.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "데이터 수집 일부 실패(계속 진행)" }

# (2) 차트 이미지 생성 → assets\charts\<오늘날짜>\*.png
Write-Host "[2/4] 차트 생성..."
& $venvPython "$repo\scripts\make_charts.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "차트 생성 실패(계속 진행)" }

# (3) 비인기 종목 후보 스크리닝 → data\<오늘날짜>\screener.json
Write-Host "[3/4] 비인기 종목 스크리닝..."
& $venvPython "$repo\scripts\screener.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "스크리너 실패(계속 진행)" }

# (4) Claude Code 헤드리스 실행 → 분석·리포트·주문서(orders) 생성 (git은 아래에서)
#   --dangerously-skip-permissions : 무인 실행이라 도구(웹검색·파일쓰기) 자동 허용
Write-Host "[4/5] 분석·리포트 생성..."
$prompt = Get-Content -Raw "$repo\prompts\daily-report.md"
& $claude -p $prompt --dangerously-skip-permissions

# (5) 가상 포트폴리오 매매 반영 + 자산곡선 차트
Write-Host "[5/5] 포트폴리오 매매 반영..."
& $venvPython "$repo\scripts\portfolio.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "포트폴리오 갱신 실패(계속 진행)" }

# 커밋 & 푸시
Write-Host "커밋·푸시..."
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  git commit -m "report: $(Get-Date -Format yyyy-MM-dd) (자동)"
  git push
} else {
  Write-Host "변경 없음 — 커밋 생략"
}

Write-Host "===== 완료: $(Get-Date) ====="
try { Stop-Transcript | Out-Null } catch {}
