# 치지직 채팅 분석기

[![Build and Release](https://github.com/YOUR_USERNAME/chzzk-chat-analyzer/actions/workflows/build.yml/badge.svg)](https://github.com/YOUR_USERNAME/chzzk-chat-analyzer/actions/workflows/build.yml)

치지직에서 export한 CSV 파일을 분석하여 키워드 빈도를 추적하고 워드클라우드를 생성하는 GUI 프로그램입니다.

## 다운로드

최신 릴리즈에서 실행 파일을 다운로드하세요:

- **Windows**: `ChzzkChatAnalyzer-Windows.zip`
- **macOS**: `ChzzkChatAnalyzer-macOS.zip`

[📥 최신 릴리즈 다운로드](https://github.com/YOUR_USERNAME/chzzk-chat-analyzer/releases/latest)

## 기능

### 1. 키워드 분석
- 특정 키워드가 방송 중 어느 시점에 많이 언급되었는지 분석
- 시간 간격을 설정하여 빈도 그래프 생성
- 가장 많이 언급된 시간대 확인
- 정규표현식 특수문자 지원 (?, *, + 등)

### 2. 프리미어 프로 마커 내보내기
- 키워드 분석 결과를 Adobe Premiere Pro에서 사용 가능한 마커 CSV로 내보내기
- 각 마커에 키워드 빈도 정보 포함

### 3. 워드클라우드 생성
- 전체 채팅 내용을 분석하여 워드클라우드 생성
- 방송의 전반적인 분위기와 주요 키워드 파악
- PNG 이미지로 저장 가능
- 크로스 플랫폼 한글 폰트 자동 감지

## 설치 및 실행

### 방법 1: 실행 파일 사용 (권장)

1. [릴리즈 페이지](https://github.com/YOUR_USERNAME/chzzk-chat-analyzer/releases)에서 OS에 맞는 파일 다운로드
2. 압축 해제
3. 실행 파일 실행
   - **Windows**: `ChzzkChatAnalyzer.exe`
   - **macOS**: `ChzzkChatAnalyzer.app`

### 방법 2: Python으로 직접 실행

```bash
# 저장소 클론
git clone https://github.com/YOUR_USERNAME/chzzk-chat-analyzer.git
cd chzzk-chat-analyzer

# 의존성 설치
pip install -r requirements.txt

# 프로그램 실행
python src/main.py
```

### 방법 3: 직접 빌드

#### macOS
```bash
chmod +x build_macos.sh
./build_macos.sh
```

실행 파일: `dist/ChzzkChatAnalyzer.app`

#### Windows
```batch
build_windows.bat
```

실행 파일: `dist\ChzzkChatAnalyzer\ChzzkChatAnalyzer.exe`

## 사용 방법

1. **CSV 파일 로드**
   - "파일 선택" 버튼 클릭
   - 치지직에서 export한 CSV 파일 선택

2. **키워드 분석**
   - 검색할 키워드 입력 (예: "ㅋㅋ", "고키겡요", "??")
   - 시간 간격 설정 (분 단위, 기본값: 1분)
   - "키워드 분석" 버튼 클릭
   - 그래프로 결과 확인

3. **프리미어 마커 내보내기**
   - 키워드 분석 후 "프리미어 마커 내보내기" 버튼 클릭
   - 저장 위치 선택

4. **워드클라우드 생성**
   - "워드클라우드 생성" 버튼 클릭
   - 필요시 "워드클라우드 저장" 버튼으로 이미지 저장

## CSV 파일 형식

치지직에서 export한 CSV는 다음 형식이어야 합니다:
- `재생시간`: HH:MM:SS 형식 (예: 00:05:30)
- `닉네임`: 사용자 닉네임
- `id`: 사용자 ID
- `메시지`: 채팅 메시지

## 프리미어 프로에서 마커 사용하기

1. Adobe Premiere Pro 열기
2. 프로젝트 패널에서 타임라인 우클릭
3. "Import Markers" 선택
4. 내보낸 CSV 파일 선택
5. 타임라인에 마커가 자동으로 추가됨

## 기술 스택

- **PyQt6** - GUI 프레임워크
- **pandas** - CSV 데이터 처리
- **matplotlib** - 그래프 시각화
- **wordcloud** - 워드클라우드 생성
- **PyInstaller** - 실행 파일 빌드

## 개발

### 요구사항
- Python 3.9+
- PyQt6
- pandas
- matplotlib
- wordcloud

### 프로젝트 구조
```
chzzk-chat-analyzer/
├── src/
│   ├── main.py              # 애플리케이션 진입점
│   ├── ui/                  # GUI 컴포넌트
│   │   ├── main_window.py
│   │   └── styles.py
│   └── core/                # 핵심 로직
│       ├── analyzer.py
│       └── wordcloud_gen.py
├── .github/
│   └── workflows/
│       └── build.yml        # GitHub Actions 빌드
├── requirements.txt
├── build.spec
└── README.md
```

## 라이선스

MIT License

## 기여

이슈와 풀 리퀘스트는 언제나 환영합니다!
