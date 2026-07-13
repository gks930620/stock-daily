# 개발 도구 설정 (Python 환경)

이 프로젝트의 데이터 수집은 Python으로 합니다. 도구 설치·격리 방식을 정리합니다.

## 설치 위치 (이 PC의 규칙)

개발 도구는 모두 **`C:\Users\gks93\tools`** 아래에 둡니다 (node, flutter 등과 동일).

- **Python 인터프리터**: `C:\Users\gks93\tools\Python312\python.exe` (3.12.10)
  - 시스템 PATH를 오염시키지 않도록 `PrependPath=0`로 설치함 (전역 오염 없음).
- **AppData 기본 위치에 설치했던 파이썬은 제거**했습니다.

## "자바처럼 전역 설치 안 하고 쓰는 법" — venv

질문 주신 부분 답: Python은 자바(JDK)처럼 인터프리터 하나를 두고, **프로젝트마다 `venv`(가상환경)로 의존성을 격리**하는 게 표준입니다. 전역에 패키지를 깔지 않으므로 "전역 오염 없음"이 보장돼요. PyCharm 같은 IDE도 결국 이 인터프리터/venv를 가리키는 방식입니다.

| 개념 | 자바 | 파이썬(이 프로젝트) |
|---|---|---|
| 런타임 | JDK (`tools`에 설치) | Python (`tools\Python312`) |
| 프로젝트별 의존성 격리 | Gradle/Maven 로컬 캐시 | **venv** (`.venv/`, 저장소 안) |
| IDE | IntelliJ | PyCharm (인터프리터로 `.venv` 지정) |

- 이 프로젝트의 패키지(yfinance 등)는 **`.venv/`** 안에만 설치됩니다. (`.gitignore`로 커밋 제외)
- 필요한 패키지 목록은 **`requirements.txt`** 에 있습니다.

## 환경 다시 만들기 (venv가 없거나 다른 PC일 때)

PowerShell에서:

```powershell
cd "C:\Users\gks93\workspace\주식시장예상클로드코드"
& "C:\Users\gks93\tools\Python312\python.exe" -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## 스크립트는 어떻게 파이썬을 쓰나

- 데이터 수집: `scripts/collect_data.py`
- 매일 실행 스크립트 `scripts/run-daily.ps1` 이 **`.venv\Scripts\python.exe`** 로 수집 스크립트를 먼저 돌린 뒤, Claude가 분석합니다.
- 수동 실행:
  ```powershell
  & ".\.venv\Scripts\python.exe" scripts\collect_data.py
  ```

## PyCharm으로 열 때

1. PyCharm에서 이 폴더 열기
2. Settings → Project → Python Interpreter → **Add Local Interpreter** → Existing → `.venv\Scripts\python.exe` 선택
3. 이후 PyCharm이 `.venv`의 패키지를 그대로 인식합니다.

## 참고

- Python을 나중에 `C:\Users\gks93\tools` 안 다른 이름으로 옮기고 싶으면: 재설치 후 `.venv`를 다시 만들면 됩니다 (venv는 인터프리터 경로를 참조하므로).
