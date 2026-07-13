# 매일 실행 스크립트 — 작업 스케줄러가 이 파일을 호출합니다.
# 순서: 저장소 이동 → (1) 파이썬으로 시세 데이터 수집 → (2) Claude가 분석·리포트 생성·push

$ErrorActionPreference = "Stop"

# 이 저장소 경로 / 프로젝트 전용 파이썬(venv)
$repo = "C:\Users\gks93\workspace\주식시장예상클로드코드"
$venvPython = "$repo\.venv\Scripts\python.exe"
Set-Location $repo

# 최신 상태로 동기화
git pull --rebase 2>&1 | Out-Null

# (1) 시세 데이터 수집 → data\<오늘날짜>\market.json 생성
Write-Host "[1/2] 데이터 수집..."
& $venvPython "$repo\scripts\collect_data.py"
if ($LASTEXITCODE -ne 0) { Write-Warning "데이터 수집 일부 실패(계속 진행)" }

# (2) Claude Code 헤드리스 실행 → 분석·리포트 생성·push
#   -p : 프롬프트 주고 결과 출력 후 종료 (헤드리스)
#   --dangerously-skip-permissions : 무인 실행이라 도구(웹검색·파일쓰기·git) 자동 허용
#     (개인 자동화용. 신뢰하는 이 저장소에서만 사용.)
Write-Host "[2/2] 분석·리포트 생성..."
$prompt = Get-Content -Raw "$repo\prompts\daily-report.md"
claude -p $prompt --dangerously-skip-permissions

Write-Host "완료: $(Get-Date)"
