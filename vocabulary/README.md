# 단어 입력기 시스템

## 환경 설정

1. `.env` 파일을 생성하고 다음 내용을 입력하세요:

```env
# MySQL Database Configuration
MYSQL_HOST=your_host
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
```

2. 필요한 패키지 설치:

```bash
pip install -r requirements.txt
```

3. 실행:

```bash
python vocab_app.py
```

## 주의사항

- `.env` 파일은 절대 Git에 커밋하지 마세요
- 실제 데이터베이스 정보는 환경 변수로 관리하세요