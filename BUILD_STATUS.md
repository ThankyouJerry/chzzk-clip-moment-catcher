# 빌드 상태 기준

현재 빌드 상태는 저장소의 [QA and Build](https://github.com/ThankyouJerry/chzzk-clip-moment-catcher/actions/workflows/build.yml) 워크플로우를 기준으로 확인합니다.

## 완료 조건

- Ubuntu, Windows, macOS 테스트 통과
- 앱 버전, 변경 이력, 태그 메타데이터 일치
- Windows x86_64 실행 파일 생성 확인
- macOS Intel 앱 생성 및 ad-hoc 서명 검증
- macOS Apple Silicon 앱 생성 및 ad-hoc 서명 검증
- 두 macOS 앱에 포함된 모든 Mach-O 파일이 macOS 12 호환 범위인지 확인
- macOS ZIP에 Finder·AppleDouble 메타데이터가 없고 압축 해제 후 서명이 유지되는지 확인
- 세 패키지에 테스트·예제·샘플 데이터·Python 소스가 포함되지 않았는지 확인
- 태그 빌드라면 세 ZIP이 GitHub Release에 첨부됨

문서에는 특정 실행이 아직 진행 중이라는 임시 상태를 기록하지 않습니다. 실제 결과와 로그는 Actions 실행 기록과 Release 자산을 확인하세요.
