# Windows + macOS 빌드 가이드

## 현재 상황

✅ **macOS 빌드**: 로컬에서 완료
❌ **Windows 빌드**: Mac에서는 불가능

---

## 해결 방법: GitHub Actions 사용 (자동 빌드)

이미 `.github/workflows/build.yml`이 설정되어 있습니다!

### 작동 방식

1. **GitHub에 푸시**
2. **Tag 생성** (예: v1.0.0)
3. **GitHub Actions 자동 실행**:
   - Windows 환경에서 Windows 빌드
   - macOS 환경에서 macOS 빌드
4. **자동으로 Release 생성**:
   - `ChzzkClipMomentCatcher-Windows.zip`
   - `ChzzkClipMomentCatcher-macOS.zip`

---

## 사용 방법

### 1. GitHub에 푸시

```bash
cd /Users/hvs/.gemini/antigravity/scratch/chzzk-clip-moment-catcher

# Git 초기화 (아직 안했다면)
git init
git add .
git commit -m "Initial commit: Chzzk Clip Moment Catcher v1.0.0"

# GitHub 저장소 연결
git remote add origin https://github.com/SamKSH/chzzk-clip-moment-catcher.git
git branch -M main
git push -u origin main
```

### 2. Tag 생성 및 푸시

```bash
# Tag 생성
git tag v1.0.0

# Tag 푸시
git push origin v1.0.0
```

### 3. GitHub Actions 확인

1. https://github.com/SamKSH/chzzk-clip-moment-catcher/actions 접속
2. "Build and Release" 워크플로우 실행 확인
3. 완료되면 자동으로 Release 생성됨

### 4. Release 확인

https://github.com/SamKSH/chzzk-clip-moment-catcher/releases

자동으로 생성된 Release에 두 파일이 첨부됨:
- `ChzzkClipMomentCatcher-Windows.zip`
- `ChzzkClipMomentCatcher-macOS.zip`

---

## 수동으로 빌드 트리거

Tag 없이 수동으로 실행하려면:

1. https://github.com/SamKSH/chzzk-clip-moment-catcher/actions
2. "Build and Release" 선택
3. "Run workflow" 클릭
4. Artifacts에서 다운로드

---

## 로컬 macOS 빌드 (이미 완료)

```bash
cd /Users/hvs/.gemini/antigravity/scratch/chzzk-clip-moment-catcher
python3 -m PyInstaller build.spec --clean --noconfirm
cd dist
zip -r ChzzkClipMomentCatcher-macOS.zip ChzzkClipMomentCatcher.app
```

파일 위치: `dist/ChzzkClipMomentCatcher-macOS.zip`

---

## 정리

**Windows 빌드를 만들려면:**
1. GitHub에 코드 푸시
2. Tag 생성 (`v1.0.0`)
3. GitHub Actions가 자동으로 Windows + macOS 빌드
4. Release에서 다운로드

**간단하게:**
```bash
git push origin main
git tag v1.0.0
git push origin v1.0.0
```

그러면 자동으로 Windows 빌드도 생성됩니다! 🎉
