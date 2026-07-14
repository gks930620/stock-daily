# 클라우드 자동화 (GitHub Actions) — 내 PC 없이 매일 자동 실행

내 컴퓨터가 꺼져 있어도 **GitHub 서버**에서 매일 자동으로 리포트를 생성·게시합니다.
Spring Boot 같은 서버를 직접 만들 필요 없이, 저장소의 워크플로 파일 하나로 동작합니다.

- **서버**: GitHub Actions (공개 저장소 → 무료)
- **분석**: Claude Code — **내 Max 플랜 사용량으로 차감** (API 토큰당 과금 ❌)
- **트리거**: 하루 3회 KST — **08:00 🇰🇷 한국장 예상글** · 18:00 수집(한국장 마감 스냅샷) · **21:00 🇺🇸 미국장 예상글** (cron은 UTC: 23:00/09:00/12:00)

파일: [.github/workflows/daily.yml](../.github/workflows/daily.yml)

---

## 과금이 어떻게 되나 (중요)

| 워크플로에 넣는 것 | 결과 |
|---|---|
| `ANTHROPIC_API_KEY` | ❌ API 토큰당 과금 — **넣지 않는다** |
| **`CLAUDE_CODE_OAUTH_TOKEN`** | ✅ **내 Max 구독 사용량에서 차감** |

- 두 개가 동시에 있으면 **API 키가 우선**되어 과금됩니다. 그래서 이 워크플로는 **OAuth 토큰만** 씁니다.
- 토큰은 `claude setup-token`으로 발급하며 **Max/Pro 구독**이 있어야 합니다.

---

## 내가 할 일 (딱 2가지)

### ① CI용 토큰 발급 (내 PC에서 1회)

> ⚠️ **가장 헷갈리는 부분.** 브라우저에 뜨는 "코드"와, 최종 "토큰"은 **다른 값**입니다.
> Secret에 넣어야 하는 건 **토큰**(`sk-ant-oat01-...`)이지, 코드(`#` 들어간 짧은 값)가 아닙니다.

터미널(또는 PowerShell)에서 순서대로:

1. **`claude setup-token`** 실행 → **URL**이 출력됨
2. 그 **URL을 브라우저로 열기** → 로그인 → **Authorize** 클릭
3. 브라우저가 **코드**(예: `AbC...#xYz...`, 92자쯤, `#` 포함)를 보여줌 → **복사**
4. ★ **아직 실행 중인 그 PowerShell 창으로 돌아가서** ★ → 복사한 코드 **붙여넣고 Enter**
   (창을 닫으면 안 됨! setup-token이 코드 입력을 기다리는 중)
5. 그제서야 터미널에 **진짜 토큰**(`sk-ant-oat01-...` 로 시작, 100자+ 긴 문자열)이 출력됨
6. ⑤의 **토큰 전체**를 복사 (이게 Secret에 넣을 값)

| 값 | 생김새 | 용도 |
|---|---|---|
| **코드** | 짧음(~92자), `#` 포함, `sk-ant-oat` 아님 | 중간 단계 (터미널에 붙여넣는 용) |
| **토큰** ✅ | 긺(100자+), **`sk-ant-oat01-`** 로 시작 | **이걸 Secret에 넣음** |

- ⚠️ 토큰은 **비밀번호처럼** 취급. 채팅·공개된 곳에 붙여넣지 마세요. (노출됐으면 재발급)
- 터미널에서 토큰이 여러 줄로 줄바꿈돼 보여도 **처음부터 끝까지 전부** 복사하세요(일부만 복사하면 401).

### ② GitHub Secret 등록

1. 브라우저에서 **https://github.com/gks930620/stock-daily/settings/secrets/actions**
2. **New repository secret** 클릭
3. **Name**: `CLAUDE_CODE_OAUTH_TOKEN`  (정확히 이 이름)
4. **Secret**: ①에서 복사한 토큰 붙여넣기
5. **Add secret**

이게 끝입니다. 이제 하루 3회(08·18·21시 KST) GitHub 서버가 알아서 실행합니다. 수동 실행 시 모드(kr/collect/us)를 고를 수 있습니다.

---

## 잘 되는지 테스트 (지금 바로)

1. **https://github.com/gks930620/stock-daily/actions**
2. 좌측 **"시장 예상 (cloud)"** 워크플로 클릭
3. 우측 **Run workflow** 버튼 → 실행
4. 몇 분 뒤 초록 체크 ✅ 뜨면 성공. 사이트(https://gks930620.github.io/stock-daily/)에 새 리포트 반영.

실패(빨간 X)하면 해당 실행을 클릭해 로그를 보면 원인이 나옵니다.

---

## 로컬 작업 스케줄러는?

클라우드로 옮겼으면 **로컬 예약은 꺼도 됩니다** (PowerShell):
```powershell
Disable-ScheduledTask -TaskName StockDailyReport      # 잠깐 끄기
# 또는
Unregister-ScheduledTask -TaskName StockDailyReport -Confirm:$false   # 완전 삭제
```
둘 다 켜두면 하루 두 번(로컬+클라우드) 생성될 수 있으니, **클라우드만 쓰는 것을 권장**합니다.

---

## 분석 모델 지정

헤드리스 실행은 `claude -p`의 **`--model`** 플래그로 모델을 지정합니다. 이 프로젝트는 **최신 Opus**로 고정:

```bash
claude -p "$PROMPT" --model opus ...
```

- `opus` = **항상 최신 Opus** (현재 4.8, 새 버전 나오면 자동 승격) ← 이 프로젝트 설정
- 특정 버전 고정을 원하면 전체 ID: `--model claude-opus-4-8`
- 다른 별칭: `sonnet`(빠르고 저렴), `haiku`(가장 저렴)
- 모델을 바꿔도 **과금은 그대로 Max 구독 사용량** (OAuth 토큰 인증이라 API 과금으로 안 바뀜)
- 수정 위치: [.github/workflows/daily.yml](../.github/workflows/daily.yml)과 [scripts/run-daily.ps1](../scripts/run-daily.ps1)의 `--model` 값

## 참고 / 솔직한 단서

- **토큰 수명 1년.** 만료되면 `claude setup-token` 다시 실행 → Secret 값 교체.
- **한국 스크리너(FinanceDataReader)** 는 네이버/KRX에서 받는데, GitHub 서버(미국)에서 **가끔 막힐 수 있습니다.** 그래서 워크플로에서 스크리너 단계는 **실패해도 계속 진행**하도록 했습니다 (그날 후보가 비어도 나머지 리포트는 정상 생성). 미국·글로벌 데이터(yfinance·FRED)는 문제 없습니다.
- **cron은 UTC 기준**이라 08:00 KST = 전날 23:00 UTC로 설정돼 있습니다. 시간을 바꾸려면 daily.yml의 cron만 수정하세요.
- GitHub은 60일간 저장소 활동이 없으면 예약 워크플로를 자동 비활성화합니다. (매일 커밋이 생기므로 사실상 문제 없음)
