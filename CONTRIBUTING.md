# 기여 가이드

치지직 클립 모먼트 캐처에 관심을 가져주셔서 감사합니다. 기능 추가나 수정 전에는 관련 이슈가 있는지 먼저 확인하고, 변경 범위를 작게 유지해 주세요.

## 개발 환경

Python 3.12 환경을 권장합니다.

```bash
python3 -m pip install -r requirements-dev.txt
```

## 테스트

Qt 창을 표시하지 않고 전체 테스트를 실행합니다.

macOS와 Linux:

```bash
QT_QPA_PLATFORM=offscreen python3 -m compileall -q src tests
QT_QPA_PLATFORM=offscreen python3 -m pytest
```

Windows PowerShell:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m compileall -q src tests
python -m pytest
```

새 동작이나 오류 수정에는 가능한 경우 회귀 테스트를 함께 추가해 주세요.

## 제출 전 확인

- 전체 테스트가 통과하는지 확인합니다.
- 사용자 데이터나 로컬 경로가 커밋에 포함되지 않았는지 확인합니다.
- UI 변경은 Windows와 macOS에서 글자 잘림과 작은 창 레이아웃을 확인합니다.
- 분석 지표를 변경했다면 계산 기준과 제한 사항을 문서에 반영합니다.

## 자동 검증과 빌드

GitHub Actions는 Ubuntu, Windows, macOS에서 테스트한 뒤 Windows x86_64와 macOS Intel·Apple Silicon 패키지를 각각 빌드합니다. 로컬 빌드, 수동 Actions 실행, 릴리스 절차는 [BUILD_GUIDE.md](BUILD_GUIDE.md)를 참고하세요.
