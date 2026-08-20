# 기여 가이드

치지직 클립 모먼트 캐처에 관심을 가져주셔서 감사합니다. 기능 추가나 수정 전에는 관련 이슈가 있는지 먼저 확인하고, 변경 범위를 작게 유지해 주세요.

## 개발 환경

Python 3.12 환경을 사용합니다. 시스템 Python에 직접 설치하지 말고 저장소 전용 가상환경을 만드세요.

기여하려면 먼저 저장소를 자신의 GitHub 계정으로 fork한 뒤 fork의 URL로 clone합니다. 단순히 소스 실행만 확인하려면 아래 원본 URL을 사용할 수 있습니다.

```bash
git clone https://github.com/ThankyouJerry/chzzk-clip-moment-catcher.git
cd chzzk-clip-moment-catcher
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: -r requirements-dev.txt
```

Windows에서는 `python3.12 -m venv .venv` 대신 `py -3.12 -m venv .venv`를 실행한 뒤 `.venv\Scripts\activate`로 활성화하세요. 앱은 다음 명령으로 실행합니다.

```bash
python src/main.py
```

## 테스트

Qt 창을 표시하지 않고 전체 테스트를 실행합니다.

macOS와 Linux:

```bash
QT_QPA_PLATFORM=offscreen python -m compileall -q src tests
QT_QPA_PLATFORM=offscreen python -m pytest
python -m pip check
```

Windows PowerShell:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m compileall -q src tests
python -m pytest
python -m pip check
```

새 동작이나 오류 수정에는 가능한 경우 회귀 테스트를 함께 추가해 주세요.

## 제출 전 확인

- 전체 테스트가 통과하는지 확인합니다.
- 사용자 데이터나 로컬 경로가 커밋에 포함되지 않았는지 확인합니다.
- UI 변경은 Windows와 macOS에서 글자 잘림과 작은 창 레이아웃을 확인합니다.
- 분석 지표를 변경했다면 계산 기준과 제한 사항을 문서에 반영합니다.
- 사용자에게 보이는 변경이라면 `CHANGELOG.md`를 갱신합니다.

## 변경 제출

1. 기존 [Issues](https://github.com/ThankyouJerry/chzzk-clip-moment-catcher/issues)를 확인하고 필요한 경우 재현 방법과 기대 동작을 포함한 이슈를 작성합니다.
2. 자신의 fork를 clone합니다. 쓰기 권한이 있는 협업자는 원본 저장소에서 바로 브랜치를 만들 수 있습니다.
3. `main`에서 한 가지 목적에 집중한 브랜치와 커밋을 만들고 자신의 fork에 push합니다.
4. 변경 이유, 검증 방법, UI 변경 화면을 설명한 Pull Request를 원본 저장소의 `main`으로 제출합니다.
5. GitHub Actions가 모두 통과하고 리뷰 의견이 반영됐는지 확인합니다.

## 자동 검증과 빌드

GitHub Actions는 Ubuntu, Windows, macOS에서 테스트한 뒤 Windows x86_64와 macOS Intel·Apple Silicon 패키지를 각각 빌드합니다. 로컬 빌드, 수동 Actions 실행, 릴리스 절차는 [BUILD_GUIDE.md](BUILD_GUIDE.md)를 참고하세요.
