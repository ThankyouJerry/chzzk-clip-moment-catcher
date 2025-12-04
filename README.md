# 치지직 클립 모먼트 캐처 (Chzzk Clip Moment Catcher)

[![Build and Release](https://github.com/YOUR_USERNAME/chzzk-clip-moment-catcher/actions/workflows/build.yml/badge.svg)](https://github.com/YOUR_USERNAME/chzzk-clip-moment-catcher/actions/workflows/build.yml)

치지직 방송의 하이라이트 순간을 찾아주는 도구입니다. CSV 채팅 데이터를 분석하여 키워드 빈도를 추적하고, 프리미어 프로 마커로 내보내어 편집 시 하이라이트 구간을 쉽게 찾을 수 있습니다.

## 다운로드

최신 릴리즈에서 실행 파일을 다운로드하세요:

- **Windows**: `ChzzkClipMomentCatcher-Windows.zip`
- **macOS**: `ChzzkClipMomentCatcher-macOS.zip`

[📥 최신 릴리즈 다운로드](https://github.com/YOUR_USERNAME/chzzk-clip-moment-catcher/releases/latest)

## 주요 기능

### 1. 키워드 빈도 분석
- 특정 키워드가 방송 중 어느 시점에 많이 언급되었는지 분석
- 시간 간격을 설정하여 빈도 그래프 생성
- 가장 많이 언급된 시간대 확인
- 정규표현식 특수문자 지원 (?, *, + 등)
- **활용**: "ㅋㅋ", "와", "대박" 등 반응이 많은 하이라이트 구간 찾기

### 2. 프리미어 프로 마커 내보내기
- 키워드 분석 결과를 Adobe Premiere Pro 마커 CSV로 내보내기
- 각 마커에 키워드 빈도 정보 포함
- **활용**: 편집 시 하이라이트 구간에 자동으로 마커 표시

### 3. 워드클라우드 생성
- 전체 채팅 내용을 분석하여 워드클라우드 생성
- 방송의 전반적인 분위기와 주요 키워드 파악
- PNG 이미지로 저장 가능
- 크로스 플랫폼 한글 폰트 자동 감지
- **활용**: 방송 썸네일이나 하이라이트 영상 제작에 활용

## 사용 시나리오

### 시나리오 1: 하이라이트 편집
1. 치지직에서 방송 채팅 CSV 다운로드
2. "ㅋㅋ" 키워드로 분석 → 시청자 반응이 많은 구간 확인
3. 프리미어 마커 내보내기
4. 프리미어 프로에서 마커 import → 하이라이트 구간 빠르게 편집

### 시나리오 2: 방송 분석
1. 여러 키워드로 분석 ("대박", "와", "??")
2. 각 키워드별 반응 시점 비교
3. 가장 반응이 좋았던 순간 파악
4. 다음 방송 기획에 활용

### 시나리오 3: 썸네일 제작
1. 워드클라우드 생성
2. 방송의 주요 키워드 확인
3. 워드클라우드 이미지를 썸네일에 활용

## 설치 및 실행

### 방법 1: 실행 파일 사용 (권장)

1. [릴리즈 페이지](https://github.com/YOUR_USERNAME/chzzk-clip-moment-catcher/releases)에서 OS에 맞는 파일 다운로드
2. 압축 해제
3. 실행 파일 실행
   - **Windows**: `ChzzkClipMomentCatcher.exe`
   - **macOS**: `ChzzkClipMomentCatcher.app`

### 방법 2: Python으로 직접 실행

```bash
# 저장소 클론
git clone https://github.com/YOUR_USERNAME/chzzk-clip-moment-catcher.git
cd chzzk-clip-moment-catcher

# 의존성 설치
pip install -r requirements.txt

# 프로그램 실행
python src/main.py
```

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

## 치지직 CSV 다운로드 방법

1. 치지직 방송 다시보기 페이지 접속
2. 채팅 창에서 설정 (⚙️) 클릭
3. "채팅 다운로드" 또는 "Export Chat" 선택
4. CSV 형식으로 저장

## 프리미어 프로에서 마커 사용하기

1. Adobe Premiere Pro 열기
2. 프로젝트 패널에서 타임라인 우클릭
3. "Import Markers" 선택
4. 내보낸 CSV 파일 선택
5. 타임라인에 마커가 자동으로 추가됨

## 기술 스택

- **PyQt6** - 크로스 플랫폼 GUI 프레임워크
- **pandas** - CSV 데이터 처리
- **matplotlib** - 그래프 시각화 (한글 폰트 지원)
- **wordcloud** - 워드클라우드 생성
- **PyInstaller** - 실행 파일 빌드
- **GitHub Actions** - 자동 빌드 및 릴리즈

## 프로젝트 구조

```
chzzk-clip-moment-catcher/
├── src/
│   ├── main.py              # 애플리케이션 진입점
│   ├── ui/                  # GUI 컴포넌트
│   │   ├── main_window.py   # 메인 윈도우
│   │   └── styles.py        # 다크 테마 스타일
│   └── core/                # 핵심 로직
│       ├── analyzer.py      # 채팅 분석 엔진
│       └── wordcloud_gen.py # 워드클라우드 생성
├── .github/
│   └── workflows/
│       └── build.yml        # 자동 빌드 워크플로우
├── requirements.txt
├── build.spec
└── README.md
```

## 라이선스

MIT License

## 기여

이슈와 풀 리퀘스트는 언제나 환영합니다!

---

**Made with ❤️ for Chzzk Streamers and Editors**
