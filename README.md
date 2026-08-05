# 치지직 클립 모먼트 캐처

[![QA and Build](https://github.com/ThankyouJerry/chzzk-clip-moment-catcher/actions/workflows/build.yml/badge.svg)](https://github.com/ThankyouJerry/chzzk-clip-moment-catcher/actions/workflows/build.yml)

치지직 VOD 채팅 CSV에서 편집 후보 구간을 찾는 로컬 데스크톱 앱입니다. 채팅 급증, 특정 키워드 급증, 정서 방향과 반응 강도를 분석하고 실제 채팅 피크를 기준으로 편집용 프리롤·포스트롤 구간을 제안합니다.

모든 분석은 사용자 컴퓨터에서 실행됩니다. CSV나 채팅 내용이 별도 서버로 전송되지 않습니다.

## 주요 기능

- 채팅량이 주변 구간보다 급증한 사건을 탐색합니다.
- `ㅋㅋ`, `레전드` 같은 키워드의 메시지 수와 실제 출현 횟수를 따로 계산합니다.
- 인접한 급증 구간을 하나의 사건으로 합치고, 원본 채팅에서 실제 피크 시각을 다시 찾습니다.
- 긍정·부정의 `정서 방향`과 반응이 얼마나 격한지 나타내는 `반응 강도`를 분리합니다.
- 결과를 탭으로 보관하고 사건 시작, 실제 피크, 채팅 수, 기준 대비 배수, 신뢰도, 참여 인원을 함께 표시합니다.
- 편집 작업표 CSV, Premiere 교환 XML, Final Cut FCPXML을 내보냅니다.
- `p001`, `p002` 형태로 나뉜 채팅 CSV를 자동으로 찾아 순서대로 합칩니다.
- 반복 반응어를 정규화한 워드클라우드를 만듭니다.

## 다운로드

[Releases](https://github.com/ThankyouJerry/chzzk-clip-moment-catcher/releases)에서 운영체제에 맞는 파일을 받습니다.

- Windows: `ChzzkClipMomentCatcher-Windows-x86_64.zip`
- macOS Apple Silicon: `ChzzkClipMomentCatcher-macOS-arm64.zip`
- macOS Intel: `ChzzkClipMomentCatcher-macOS-x86_64.zip`

macOS 빌드는 ad-hoc 서명되며 Apple 공증은 적용되지 않습니다. 처음 실행할 때 시스템 설정의 `개인정보 보호 및 보안`에서 실행을 허용해야 할 수 있습니다.

## Python으로 실행

Python 3.12 환경을 권장합니다.

```bash
git clone https://github.com/ThankyouJerry/chzzk-clip-moment-catcher.git
cd chzzk-clip-moment-catcher
python3 -m pip install -r requirements.txt
python3 src/main.py
```

## CSV 준비

[chzzk-chat-exporter](https://github.com/ThankyouJerry/chzzk-chat-exporter)에서 내보낸 CSV를 사용할 수 있습니다. 필수 열은 다음 세 개이며 `id` 같은 추가 열은 유지됩니다.

```csv
재생시간,닉네임,id,메시지
00:00:18,사용자A,abc123,{:customEmote:}
00:00:19,사용자B,def456,ㅋㅋㅋㅋ
```

- `재생시간`: `HH:MM:SS` 또는 `HH:MM:SS.sss`
- `닉네임`: 채팅 작성자 이름
- `메시지`: 원본 채팅 내용

분할 파일 이름이 `방송_d_p001.csv`, `방송_d_p002.csv` 형식이면 어느 파일을 선택해도 전체 묶음을 확인합니다. 첫 파일이나 중간 파일이 빠졌거나 열 구성이 다르면 분석하지 않고 정확한 오류를 표시합니다.

## 사용 방법

1. `파일 선택`에서 채팅 CSV를 불러옵니다.
2. `채팅 밀도 분석`, `키워드 분석`, `정서·반응 강도 분석` 중 하나를 실행합니다.
3. 결과 탭에서 전체 타임라인과 사건별 근거를 확인합니다.
4. 편집 후보가 적절한지 VOD 화면과 함께 검토합니다.
5. `편집 연동`에서 프리롤, 포스트롤, FPS와 출력 형식을 선택합니다.

민감도가 높을수록 작은 변화도 더 많이 포착합니다. 짧은 영상처럼 시간 구간이 3개 미만이면 통계 판정을 강행하지 않고 `근거 부족`으로 표시합니다.

## 편집 연동

### 편집 작업표 CSV

추천 시작, 실제 피크, 추천 종료, 채팅 수와 신뢰도를 표로 저장합니다. 사람이 검토하거나 스프레드시트에서 작업을 배분하기 위한 형식이며 편집 프로그램의 네이티브 프로젝트 파일은 아닙니다.

### Premiere 교환 XML

Final Cut Pro 7 XML 형식의 시퀀스 마커를 만듭니다. Adobe는 Final Cut Pro XML을 가져올 때 시퀀스 마커를 유지하는 교환 절차를 안내합니다. Premiere 버전과 기존 시퀀스 설정에 따라 결과가 달라질 수 있으므로 원본 프로젝트 복사본에서 먼저 확인하세요.

- [Adobe Final Cut Pro XML 가져오기 안내](https://helpx.adobe.com/premiere-pro/using/importing-xml-project-files-final.html)

### Final Cut FCPXML

마커 전용 FCPXML 프로젝트를 만듭니다. 지원 FPS는 `23.976`, `24`, `25`, `29.97`, `30`, `50`, `59.94`, `60`입니다.

- [Apple FCPXML Reference](https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference)

XML 구조와 프레임 변환은 자동 테스트하지만, 모든 Premiere·Final Cut 버전에서의 실제 가져오기를 보증하지는 않습니다.

## 지표 해석

### 채팅 사건

현재 구간을 제외한 주변 구간의 중앙값과 변동 폭을 기준선으로 사용합니다. 기준선을 충분히 넘는 후보가 서로 인접하면 하나의 사건으로 합칩니다. 마커는 시간 구간의 시작점이 아니라 사건 안에서 가장 밀집된 15초 채팅의 중앙 시각에 생성됩니다.

### 신뢰도

신뢰도는 통계적 확률이 아닙니다. 기준선 대비 변화 크기, 기준 대비 배수, 참여자 다양성을 0~1 범위로 요약한 검토 우선순위입니다. 한 사용자가 대부분의 채팅을 차지하면 신뢰도가 낮아질 수 있습니다.

### 정서 방향과 반응 강도

- 정서 방향: `-1`에 가까울수록 부정, `+1`에 가까울수록 긍정입니다.
- 반응 강도: 웃음, 울음, 놀람, 반복 문장부호, 커스텀 이모트가 얼마나 강한지 나타냅니다.
- 근거 커버리지: 해당 구간 메시지 중 정서 방향을 판단할 표현이 있었던 비율입니다.

이 분석은 한국어 채팅 휴리스틱이며 영상·음성의 의미를 이해하는 AI 모델이 아닙니다. 풍자, 밈, 스트리머별 은어는 오판할 수 있으므로 편집 전 원본 VOD 확인이 필요합니다.

## 개발 및 테스트

```bash
python3 -m pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python3 -m pytest
```

GitHub Actions는 Ubuntu, Windows, macOS에서 테스트한 뒤 Windows x86_64와 macOS Intel·Apple Silicon 패키지를 각각 빌드합니다. 자세한 내용은 [BUILD_GUIDE.md](BUILD_GUIDE.md)를 참고하세요.

버전별 수정 내용은 [CHANGELOG.md](CHANGELOG.md)에서 확인할 수 있습니다.

## 개인정보와 저작권

채팅 CSV에는 닉네임과 식별 정보가 포함될 수 있습니다. 공유 전에 개인정보와 플랫폼 정책을 확인하세요. 분석 결과와 다운로드한 영상의 사용 책임은 사용자에게 있으며 영상과 방송 콘텐츠의 저작권은 원 저작권자에게 있습니다.

## 라이선스

MIT License
