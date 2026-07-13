# 클라우드 자동화 (GitHub Actions) — 내 PC 없이 매일 자동 실행

내 컴퓨터가 꺼져 있어도 **GitHub 서버**에서 매일 자동으로 리포트를 생성·게시합니다.
Spring Boot 같은 서버를 직접 만들 필요 없이, 저장소의 워크플로 파일 하나로 동작합니다.

- **서버**: GitHub Actions (공개 저장소 → 무료)
- **분석**: Claude Code — **내 Max 플랜 사용량으로 차감** (API 토큰당 과금 ❌)
- **트리거**: 매일 08:00 KST (워크플로 cron `0 23 * * *` = UTC 23:00 전날)

파일: [.github/workflows/daily.yml](.github/workflows/daily.yml)

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

터미널(또는 PowerShell)에서:
```
claude setup-token
```
- 브라우저로 로그인 인증이 진행되고, **1년짜리 토큰**이 화면에 출력됩니다.
- 그 토큰 문자열을 복사해 둡니다. (아무데도 저장 안 됨 — 이 화면에서만 복사)
- ⚠️ 이 토큰은 **비밀번호처럼** 취급하세요. 공개된 곳에 붙여넣지 마세요.

### ② GitHub Secret 등록

1. 브라우저에서 **https://github.com/gks930620/stock-daily/settings/secrets/actions**
2. **New repository secret** 클릭
3. **Name**: `CLAUDE_CODE_OAUTH_TOKEN`  (정확히 이 이름)
4. **Secret**: ①에서 복사한 토큰 붙여넣기
5. **Add secret**

이게 끝입니다. 이제 매일 08:00 KST에 GitHub 서버가 알아서 리포트를 만들어 push합니다.

---

## 잘 되는지 테스트 (지금 바로)

1. **https://github.com/gks930620/stock-daily/actions**
2. 좌측 **"매일 주식 리포트 (cloud)"** 워크플로 클릭
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

## 참고 / 솔직한 단서

- **토큰 수명 1년.** 만료되면 `claude setup-token` 다시 실행 → Secret 값 교체.
- **한국 스크리너(FinanceDataReader)** 는 네이버/KRX에서 받는데, GitHub 서버(미국)에서 **가끔 막힐 수 있습니다.** 그래서 워크플로에서 스크리너 단계는 **실패해도 계속 진행**하도록 했습니다 (그날 후보가 비어도 나머지 리포트는 정상 생성). 미국·글로벌 데이터(yfinance·FRED)는 문제 없습니다.
- **cron은 UTC 기준**이라 08:00 KST = 전날 23:00 UTC로 설정돼 있습니다. 시간을 바꾸려면 daily.yml의 cron만 수정하세요.
- GitHub은 60일간 저장소 활동이 없으면 예약 워크플로를 자동 비활성화합니다. (매일 커밋이 생기므로 사실상 문제 없음)
