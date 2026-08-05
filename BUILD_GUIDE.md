# 빌드 가이드

## 지원 환경

| 대상 | GitHub Actions 러너 | 결과 파일 |
|---|---|---|
| Windows x86_64 | `windows-latest` | `ChzzkClipMomentCatcher-Windows-x86_64.zip` |
| macOS Intel | `macos-15-intel` | `ChzzkClipMomentCatcher-macOS-x86_64.zip` |
| macOS Apple Silicon | `macos-14` | `ChzzkClipMomentCatcher-macOS-arm64.zip` |

워크플로우는 Python 3.12와 고정된 의존성을 사용합니다. 모든 운영체제 테스트가 통과해야 빌드가 시작됩니다.

## 로컬 QA

```bash
python3 -m pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python3 -m compileall -q src tests
QT_QPA_PLATFORM=offscreen python3 -m pytest
```

Windows PowerShell에서는 환경 변수를 다음처럼 설정합니다.

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest
```

## 로컬 빌드

macOS:

```bash
./build_macos.sh
```

Windows:

```bat
build_windows.bat
```

PyInstaller는 실행 중인 운영체제용 패키지만 만들 수 있습니다. macOS에서 Windows 실행 파일을 직접 만들지 않고 GitHub Actions의 Windows 러너를 사용합니다.

## Actions 수동 실행

1. 저장소의 `Actions` 탭을 엽니다.
2. `QA and Build` 워크플로우를 선택합니다.
3. `Run workflow`를 실행합니다.
4. 성공한 실행의 Artifacts에서 운영체제별 ZIP을 받습니다.

## 릴리즈

`v`로 시작하는 태그를 푸시하면 테스트와 세 플랫폼 빌드가 모두 성공한 뒤 GitHub Release가 생성됩니다.

```bash
git tag v1.2.0
git push origin v1.2.0
```

태그는 코드의 `src/version.py` 버전과 일치시켜야 합니다. 태그 생성과 릴리즈 게시는 기능 검증이 끝난 뒤 명시적으로 진행합니다.

## macOS 서명 한계

Actions와 로컬 스크립트는 클라우드 폴더가 추가하는 Finder 메타데이터의 영향을 피하기 위해 임시 경로에서 앱을 정리한 뒤 ad-hoc 서명을 적용합니다. 이어서 `codesign --verify --deep --strict` 검증과 패키지 실행 확인을 수행합니다. Apple Developer ID 서명과 공증은 포함하지 않으므로 배포 환경에서는 Gatekeeper 확인이 나타날 수 있습니다.
