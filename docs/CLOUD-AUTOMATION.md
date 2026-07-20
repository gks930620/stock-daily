# 클라우드 자동화 (GitHub Actions) — 내 PC 없이 매일 자동 실행

내 컴퓨터가 꺼져 있어도 **GitHub 서버**에서 매일 자동으로 리포트를 생성·게시합니다.
Spring Boot 같은 서버를 직접 만들 필요 없이, 저장소의 워크플로 파일 하나로 동작합니다.

- **서버**: GitHub Actions (공개 저장소 → 무료)
- **분석**: Claude Code — **내 Max 플랜 사용량으로 차감** (API 토큰당 과금 ❌)
- **트리거**: 하루 2회 평일 KST(장중) — **🇰🇷 14:30 분석→14:45 발행** · **🇺🇸 23:30 분석→23:45 발행**. GitHub 예약실행은 **최대 2~3시간 지연**되므로, cron을 목표보다 ~3.5h 일찍(`0 2` / `0 11` UTC) 걸고 워크플로가 목표 시각까지 대기해 **발행 시각을 고정**한다.

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

이게 끝입니다. 이제 **평일 하루 2회**(🇰🇷 14:45 · 🇺🇸 23:45 발행) GitHub 서버가 알아서 실행합니다. 수동 실행 시 모드(kr/us)를 고를 수 있습니다.

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
Disable-ScheduledTask -TaskName StockDailyReport      # 잠깐 끄기 (구 단일 작업명. 3분할 등록했다면 StockDaily-*)
# 또는
Unregister-ScheduledTask -TaskName StockDailyReport -Confirm:$false   # 완전 삭제
```
둘 다 켜두면 하루 두 번(로컬+클라우드) 생성될 수 있으니, **클라우드만 쓰는 것을 권장**합니다.

---

## 분석 모델 · 추론 강도(effort) 지정

헤드리스 실행은 `claude -p`의 플래그로 **모델**과 **추론 강도(effort)** 를 지정합니다. 모델은 **최신 Opus**로 고정하고, effort는 **역할별로 다르게** 줍니다:

| 역할 | 세션 수 | effort | 이유 |
|---|---|---|---|
| 🛡️🚀🎯 **매니저 3인** (매매 결정) | 3 | `high` | 비용 관리 — 회차당 4세션이라 다 xhigh면 토큰 소모가 큼 |
| 🧠 **애널리스트** (3인 종합 리포트) | 1 | `xhigh` | 종합·판정이 가장 어려운 일 |

```bash
claude -p "$PROMPT" --model opus --effort high  ...   # 매니저 3인
claude -p "$PROMPT" --model opus --effort xhigh ...   # 애널리스트
```

**모델 (`--model`)**
- `opus` = **항상 최신 Opus** (현재 4.8, 새 버전 나오면 자동 승격) ← 이 프로젝트 설정
- 특정 버전 고정을 원하면 전체 ID: `--model claude-opus-4-8`
- 다른 별칭: `sonnet`(빠르고 저렴), `haiku`(가장 저렴)

**추론 강도 (`--effort`)**
- Opus 4.8 지원 값: `low` · `medium` · `high`(기본) · `xhigh` · `max`
- 이 프로젝트: 애널리스트 `xhigh` / 매니저 3인 `high` (`max`는 과추론 경향이라 제외)
- **헤드리스에선 반드시 실행 시 `--effort`로 줄 것.** `-p` 안에서 `/effort`로 바꾸면 그 세션에 저장되지 않고, Opus 4.8은 "모델 기본값 유지" 때문에 무시된다(문서 확인). settings.json의 `effortLevel`보다 CLI 플래그가 확실.

**thinking(확장 사고)에 대해 — 오해 주의**
- Opus 4.8은 **적응형 추론(adaptive reasoning)** 모델이라, thinking을 켜고 끄는 별도 스위치가 핵심이 아니다. **effort 수준이 thinking의 양을 결정**한다 → `--effort xhigh`면 이미 "필요할 때 깊게 생각"이 항상 켜진 상태.
- 예전 모델식 `MAX_THINKING_TOKENS`나 `/config`의 thinking 토글은 4.8에선 사실상 effort에 흡수됨. 그래서 우리는 **effort xhigh 하나로 "thinking 기본 ON + 최고 강도"를 동시에 달성**한다.

- 과금: 모델·effort를 바꿔도 **Max 구독 사용량에서 차감**(OAuth 토큰 인증이라 API 과금으로 안 바뀜). 단 **effort가 높을수록 토큰 소모↑** → Max 리밋 소진이 빨라질 수 있음(하루 2회 글이면 통상 문제 없음).
- 수정 위치: [.github/workflows/daily.yml](../.github/workflows/daily.yml)과 [scripts/run-daily.ps1](../scripts/run-daily.ps1)의 `--model`·`--effort` 값

## 참고 / 솔직한 단서

- **토큰 수명 1년.** 만료되면 `claude setup-token` 다시 실행 → Secret 값 교체.
- **한국 스크리너(FinanceDataReader)** 는 네이버/KRX에서 받는데, GitHub 서버(미국)에서 **가끔 막힐 수 있습니다.** 그래서 워크플로에서 스크리너 단계는 **실패해도 계속 진행**하도록 했습니다 (그날 후보가 비어도 나머지 리포트는 정상 생성). 미국·글로벌 데이터(yfinance·FRED)는 문제 없습니다.
- **cron은 UTC 기준**(KST = UTC+9). 크론(`0 2`/`0 11`)은 '충분히 일찍' 걸어두는 용도이고, **실제 발행 시각을 정하는 건 `모드 결정` 스텝의 `TARGET`(14:30/23:30)** 입니다. 발행 시각을 바꾸려면 TARGET을 고치고, 크론이 그보다 ~3.5h 이상 이르도록 유지하세요.
- GitHub은 60일간 저장소 활동이 없으면 예약 워크플로를 자동 비활성화합니다. (매일 커밋이 생기므로 사실상 문제 없음)
