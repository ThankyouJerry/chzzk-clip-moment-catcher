# 치지직 클립 모먼트 캐처 (Chzzk Clip Moment Catcher)

[![Build and Release](https://github.com/YOUR_USERNAME/chzzk-clip-moment-catcher/actions/workflows/build.yml/badge.svg)](https://github.com/YOUR_USERNAME/chzzk-clip-moment-catcher/actions/workflows/build.yml)

치지직 방송의 하이라이트 순간을 찾아주는 도구입니다. CSV 채팅 데이터를 분석하여 키워드 빈도를 추적하고, 프리미어 프로 마커로 내보내어 편집 시 하이라이트 구간을 쉽게 찾을 수 있습니다.

## 📥 다운로드 및 설치

### 방법 1: Python으로 실행 (권장)

Python이 설치되어 있다면 소스 코드를 직접 실행할 수 있습니다.

#### 1. Python 설치 확인

```bash
python3 --version
# 또는
python --version
```

Python 3.8 이상이 필요합니다. 없다면 [python.org](https://www.python.org/downloads/)에서 다운로드하세요.

#### 2. 저장소 복제

```bash
git clone https://github.com/SamKSH/chzzk-clip-moment-catcher.git
cd chzzk-clip-moment-catcher
```

또는 ZIP 다운로드:
1. https://github.com/SamKSH/chzzk-clip-moment-catcher 접속
2. 녹색 "Code" 버튼 → "Download ZIP"
3. 압축 해제 후 터미널에서 해당 폴더로 이동

#### 3. 의존성 설치

```bash
pip3 install -r requirements.txt
# 또는
pip install -r requirements.txt
```

**필요한 패키지:**
- PyQt6 (GUI 프레임워크)
- pandas (데이터 처리)
- matplotlib (그래프 생성)
- wordcloud (워드클라우드 생성)
- Pillow (이미지 처리)

#### 4. 실행

```bash
python3 src/main.py
# 또는
python src/main.py
```

---

### 방법 2: 실행 파일 사용

Python 설치 없이 바로 사용하고 싶다면:

1. [Releases](https://github.com/SamKSH/chzzk-clip-moment-catcher/releases) 페이지 접속
2. 최신 버전에서 OS에 맞는 파일 다운로드
   - **macOS**: `ChzzkClipMomentCatcher-macOS.zip`
   - **Windows**: `ChzzkClipMomentCatcher-Windows.zip` (GitHub Actions로 자동 빌드)
3. 압축 해제 후 실행

**macOS 보안 경고 해결:**
```bash
# 터미널에서 실행
xattr -cr ChzzkClipMomentCatcher.app
```

또는 `시스템 환경설정` → `보안 및 개인 정보 보호` → `확인 없이 열기`

---

## 🎯 사용 방법

### 1. CSV 파일 준비

치지직 채팅 CSV 파일이 필요합니다. 

**치지직 채팅 내보내기 확장프로그램 사용:**
1. [Chzzk Chat Exporter](https://github.com/SamKSH/chzzk-chat-exporter) 설치
2. 치지직 VOD 페이지에서 채팅 수집
3. CSV로 내보내기

**CSV 형식:**
```csv
Timestamp,User ID,Message
2025-12-05T07:30:00.000Z,user123,안녕하세요!
2025-12-05T07:30:05.123Z,user456,ㅋㅋㅋㅋ
```

### 2. 프로그램 실행

```bash
python3 src/main.py
```

### 3. CSV 파일 로드

1. **"파일 선택"** 버튼 클릭
2. 치지직에서 export한 CSV 파일 선택
3. 파일이 로드되면 상태 표시줄에 메시지 수 표시

### 4. 키워드 분석

1. **검색할 키워드 입력**
   - 예: `ㅋㅋ`, `고키겡요`, `??`, `대박`, `와`
   - 정규표현식 특수문자 지원 (?, *, + 등)

2. **시간 간격 설정** (분 단위)
   - 기본값: 1분
   - 추천: 1-5분 (영상 길이에 따라 조정)

3. **"키워드 분석"** 버튼 클릭

4. **결과 확인**
   - 그래프로 시간대별 키워드 빈도 표시
   - 가장 많이 언급된 시간대 확인

### 5. 프리미어 프로 마커 내보내기

1. 키워드 분석 후 **"프리미어 마커 내보내기"** 버튼 클릭
2. 저장 위치 선택
3. CSV 파일 생성됨

**프리미어 프로에서 사용:**
1. Adobe Premiere Pro 열기
2. 타임라인 우클릭 → **"Import Markers"**
3. 내보낸 CSV 파일 선택
4. 타임라인에 마커가 자동으로 추가됨

### 6. 워드클라우드 생성

1. **"워드클라우드 생성"** 버튼 클릭
2. 전체 채팅 내용을 분석하여 워드클라우드 표시
3. (선택) **"워드클라우드 저장"** 버튼으로 PNG 이미지 저장

---

## 💡 사용 팁

### 효과적인 키워드 선택

- **반응 키워드**: `ㅋㅋ`, `ㅎㅎ`, `ㄷㄷ` - 웃긴 순간 찾기
- **놀람 키워드**: `와`, `헐`, `대박` - 놀라운 순간 찾기
- **의문 키워드**: `??`, `뭐`, `왜` - 혼란스러운 순간 찾기
- **칭찬 키워드**: `고키겡요`, `굿`, `잘` - 잘한 순간 찾기

### 시간 간격 설정

- **짧은 영상 (10-30분)**: 1분 간격
- **중간 영상 (30-60분)**: 2-3분 간격
- **긴 영상 (1시간 이상)**: 5분 간격

### 여러 키워드 비교

1. 첫 번째 키워드 분석
2. 스크린샷 또는 메모
3. 두 번째 키워드 분석
4. 결과 비교하여 최고의 순간 찾기

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
