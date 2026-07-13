# 매일 실행 스크립트 — 작업 스케줄러가 이 파일을 호출합니다.
# 하는 일: 저장소로 이동 → Claude Code를 헤드리스로 실행 → daily-report.md 지시대로 리포트 생성·push

$ErrorActionPreference = "Stop"

# 이 저장소 경로
$repo = "C:\Users\gks93\workspace\주식시장예상클로드코드"
Set-Location $repo

# 최신 상태로 동기화 (원격에 변경이 있을 수 있으므로)
git pull --rebase 2>&1 | Out-Null

# 실행할 지시문 (prompts/daily-report.md 내용을 그대로 프롬프트로 전달)
$prompt = Get-Content -Raw "$repo\prompts\daily-report.md"

# Claude Code를 무인(헤드리스)으로 실행.
#  -p : 프롬프트를 주고 결과를 출력한 뒤 종료 (헤드리스 모드)
#  --dangerously-skip-permissions : 무인 실행이라 권한 프롬프트 없이 도구(웹검색·파일쓰기·git) 사용 허용
#    (개인 자동화용. 신뢰하는 이 저장소에서만 사용하세요.)
claude -p $prompt --dangerously-skip-permissions

Write-Host "완료: $(Get-Date)"
