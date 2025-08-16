# 국어 독해 분석기

Flask 기반의 국어 독해 학습 도구입니다. AI를 활용하여 지문을 분석하고 핵심 문단을 찾아줍니다.

## 주요 기능

- **지문 입력 및 분석**: 국어 지문을 입력하면 자동으로 문단별로 분리
- **AI 핵심 문단 추천**: Google Gemini API를 사용한 지능형 핵심 문단 분석
- **대화형 UI**: 사용자가 직접 핵심 문단을 선택하고 AI 추천과 비교 가능
- **근거 제시**: AI가 핵심 문단을 추천한 이유를 명확하게 설명

## 기술 스택

- **Backend**: Flask, Flask-CORS
- **AI**: Google Generative AI (Gemini 2.5 Pro)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Data Storage**: LocalStorage (Client-side)

## 설치 방법

1. 저장소 클론
```bash
git clone [your-repository-url]
cd wordschool/python
```

2. 가상환경 생성 및 활성화
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. 필요한 패키지 설치
```bash
pip install flask flask-cors google-generativeai
```

4. Gemini API 키 설정
   - [Google AI Studio](https://makersuite.google.com/app/apikey)에서 API 키 발급
   - `app.py` 파일의 13번째 줄에 있는 `GEMINI_API_KEY` 값을 실제 API 키로 교체

## 실행 방법

```bash
python app.py
```

브라우저에서 http://127.0.0.1:5000 접속

## 사용 방법

1. **1단계: 지문 입력하기**
   - 분석하고자 하는 국어 지문을 입력창에 붙여넣기
   - "지문 분석 시작" 버튼 클릭

2. **2단계: 핵심 문단 찾기**
   - 분리된 문단들 중 핵심이라고 생각하는 문단 클릭
   - "AI 추천 문단 보기" 버튼을 클릭하여 AI의 분석 결과 확인
   - AI가 추천한 문단과 그 근거를 확인

3. **3-5단계** (개발 중)
   - 관계 파악하기
   - 구조화 및 주제 도출
   - 문제 해결 훈련

## 프로젝트 구조

```
wordschool/python/
├── app.py              # Flask 백엔드 서버
├── templates/          # HTML 템플릿
│   ├── index.html      # 1단계: 지문 입력 페이지
│   └── step2.html      # 2단계: 핵심 문단 찾기 페이지
├── venv/               # Python 가상환경
├── .gitignore          # Git 제외 파일 목록
└── README.md           # 프로젝트 문서

```

## API 엔드포인트

- `GET /` - 1단계 페이지 렌더링
- `GET/POST /step2` - 2단계 페이지 렌더링
- `POST /analyze_passage` - 지문 분석 및 AI 추천 API

## 주의사항

- 현재 개발 단계이므로 API 키가 코드에 직접 포함되어 있습니다
- 실제 배포 시에는 환경 변수를 사용하여 API 키를 관리해야 합니다
- Flask 개발 서버를 사용 중이므로 프로덕션 환경에서는 WSGI 서버 사용 권장

## 라이선스

MIT License

## 기여

Pull Request와 Issue는 언제든 환영합니다!