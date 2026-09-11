# 빌드 가이드

## 지원 환경

| 대상 | GitHub Actions 러너 | 결과 파일 |
|---|---|---|
| Windows x86_64 | `windows-latest` | `ChzzkClipMomentCatcher-Windows-x86_64.zip` |
| macOS Intel | `macos-15-intel` | `ChzzkClipMomentCatcher-macOS-x86_64.zip` |
| macOS Apple Silicon | `macos-14` | `ChzzkClipMomentCatcher-macOS-arm64.zip` |

워크플로우는 Python 3.12, 고정된 최상위·간접 의존성, 공식 바이너리 휠을 사용합니다. 외부 Actions는 검토한 커밋 SHA로 고정되어 있으며 모든 운영체제 테스트가 통과해야 빌드가 시작됩니다.

## 로컬 QA

개발 의존성 설치와 운영체제별 테스트 명령은 [CONTRIBUTING.md의 테스트 절차](CONTRIBUTING.md#테스트)를 기준으로 사용합니다. `scripts/verify_release_version.py`는 앱 버전과 변경 이력, 태그가 일치하는지 검사합니다.

## 로컬 빌드

CI와 동일한 Python 3.12가 필요합니다. macOS 스크립트는 `python3.12`를 우선 탐색하며, 다른 경로를 써야 하면 `PYTHON_BIN=/path/to/python3.12`로 지정합니다. 배포용 macOS ZIP은 사용 중인 Python 런타임 자체가 macOS 12와 호환되어야 하며, 스크립트가 번들 안의 모든 Mach-O 파일을 검사해 더 높은 버전 전용 런타임을 차단합니다.

macOS:

```bash
./build_macos.sh
```

Windows:

```bat
build_windows.bat
```

PyInstaller는 실행 중인 운영체제용 패키지만 만들 수 있습니다. macOS에서 Windows 실행 파일을 직접 만들지 않고 GitHub Actions의 Windows 러너를 사용합니다.

두 로컬 빌드 스크립트는 `.build-venv` 전용 환경을 새로 만들고 테스트를 통과한 뒤 패키징합니다. 생성된 앱과 ZIP은 `scripts/verify_package_contents.py`로 검사해 테스트·예제·샘플 데이터·Python 소스가 포함되지 않았는지 확인합니다. 패키지 실행 확인은 창이 유지되는지만 보지 않고 작은 합성 CSV를 불러와 분석한 뒤 FCPXML을 내보내고 다시 파싱하는 기능 점검도 수행합니다.

## Actions 수동 실행

1. 저장소의 `Actions` 탭을 엽니다.
2. `QA and Build` 워크플로우를 선택합니다.
3. `Run workflow`를 실행합니다.
4. 성공한 실행의 Artifacts에서 운영체제별 ZIP을 받습니다.

## 릴리즈

`v`로 시작하는 태그를 푸시하면 테스트와 세 플랫폼 빌드가 모두 성공한 뒤 GitHub Release가 생성됩니다.

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```

태그는 코드의 `src/version.py` 버전 및 `CHANGELOG.md`의 릴리스 항목과 일치해야 합니다. 태그 생성과 릴리즈 게시는 기능 검증이 끝난 뒤 명시적으로 진행합니다.

## macOS 서명 한계

Actions와 로컬 스크립트는 클라우드 폴더가 추가하는 Finder 메타데이터의 영향을 피하기 위해 임시 경로에서 앱을 정리한 뒤 ad-hoc 서명을 적용합니다. 이어서 `codesign --verify --deep --strict` 검증, 모든 Mach-O 파일의 macOS 12 호환성 검사와 패키지 실행 확인을 수행합니다. ZIP에는 Finder·AppleDouble 메타데이터를 넣지 않고, 압축을 다시 푼 앱의 서명도 재검증합니다. Apple Developer ID 서명과 공증은 포함하지 않으므로 배포 환경에서는 Gatekeeper 확인이 나타날 수 있습니다.
