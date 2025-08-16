from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import io

app = Flask(__name__)

# 데이터베이스 설정 (MySQL 원격 서버)
# SQLite에서 MySQL로 변경
# app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "vocabulary.db")}'

# MySQL 원격 데이터베이스 설정
# 환경 변수에서 가져오기 (보안을 위해)
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'vocabulary')

# MySQL 연결 문자열
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 3600,  # 1시간마다 연결 재활용
    'pool_pre_ping': True,  # 연결 확인
}

db = SQLAlchemy(app)

# 데이터베이스 모델 정의
class Word(db.Model):
    __tablename__ = 'vocabulary_words'  # 테이블명 변경 (기존 테이블과 충돌 방지)
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    word = db.Column(db.String(100), nullable=False)
    meaning = db.Column(db.Text, nullable=False)
    initial = db.Column(db.String(50))  # 초성
    example = db.Column(db.Text)  # 예문
    
    # 메타 정보
    grade = db.Column(db.Integer)  # 학년
    source = db.Column(db.String(200))  # 출처
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'word': self.word,
            'meaning': self.meaning,
            'initial': self.initial,
            'example': self.example,
            'grade': self.grade,
            'source': self.source,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

# 메인 페이지 (단어 입력)
@app.route('/')
def index():
    return render_template('input.html')

# 단어 조회 페이지
@app.route('/search')
def search():
    return render_template('search.html')

# 단어 입력 API
@app.route('/api/words/bulk', methods=['POST'])
def bulk_insert_words():
    try:
        data = request.get_json()
        text_data = data.get('text', '')
        grade = data.get('grade')
        source = data.get('source', '')
        
        if not text_data:
            return jsonify({'error': '입력 데이터가 없습니다.'}), 400
        
        # 줄 단위로 분리
        lines = text_data.strip().split('\n')
        success_count = 0
        error_count = 0
        errors = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # "|"로 구분
            parts = line.split('|')
            
            if len(parts) < 2:
                error_count += 1
                errors.append(f"라인 {line_num}: 최소 단어와 뜻이 필요합니다.")
                continue
            
            # 데이터 추출
            word_text = parts[0].strip()
            meaning = parts[1].strip()
            initial = parts[2].strip() if len(parts) > 2 else ""
            example = parts[3].strip() if len(parts) > 3 else ""
            
            # 데이터베이스에 저장
            new_word = Word(
                word=word_text,
                meaning=meaning,
                initial=initial,
                example=example,
                grade=grade,
                source=source
            )
            
            try:
                db.session.add(new_word)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append(f"라인 {line_num}: {str(e)}")
        
        # 커밋
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'성공: {success_count}개, 실패: {error_count}개',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 단어 조회 API
@app.route('/api/words', methods=['GET'])
def get_words():
    try:
        # 쿼리 파라미터
        grade = request.args.get('grade', type=int)
        search_word = request.args.get('word', '')
        source = request.args.get('source', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # 쿼리 빌드
        query = Word.query
        
        if grade:
            query = query.filter_by(grade=grade)
        if search_word:
            query = query.filter(Word.word.contains(search_word))
        if source:
            query = query.filter(Word.source.contains(source))
        
        # 정렬 (최신순)
        query = query.order_by(Word.created_at.desc())
        
        # 페이지네이션
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'words': [word.to_dict() for word in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# PDF 다운로드 API
@app.route('/api/words/download-pdf', methods=['POST'])
def download_pdf():
    try:
        data = request.get_json()
        word_ids = data.get('word_ids', [])
        fields = data.get('fields', ['word', 'meaning'])  # 다운로드할 필드
        
        if not word_ids:
            return jsonify({'error': '다운로드할 단어를 선택해주세요.'}), 400
        
        # 선택된 단어들 조회
        words = Word.query.filter(Word.id.in_(word_ids)).all()
        
        if not words:
            return jsonify({'error': '선택된 단어가 없습니다.'}), 404
        
        # 한글 폰트 등록
        pdfmetrics.registerFont(UnicodeCIDFont('HYSMyeongJo-Medium'))
        pdfmetrics.registerFont(UnicodeCIDFont('HYGothic-Medium'))
        
        # PDF 생성
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # 스타일 설정 (한글 폰트 적용)
        styles = getSampleStyleSheet()
        
        # 한글 제목 스타일
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='HYGothic-Medium',
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=1  # 중앙 정렬
        )
        
        # 한글 본문 스타일
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontName='HYSMyeongJo-Medium',
            fontSize=11,
            leading=14
        )
        
        # 제목
        story.append(Paragraph("단어 목록", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # 테이블 데이터 준비
        table_data = []
        
        # 헤더
        header = []
        if 'word' in fields:
            header.append('단어')
        if 'meaning' in fields:
            header.append('뜻')
        if 'initial' in fields:
            header.append('초성')
        if 'example' in fields:
            header.append('예문')
        if 'grade' in fields:
            header.append('학년')
        if 'source' in fields:
            header.append('출처')
        
        table_data.append(header)
        
        # 데이터 행
        for word in words:
            row = []
            if 'word' in fields:
                row.append(word.word)
            if 'meaning' in fields:
                row.append(word.meaning)
            if 'initial' in fields:
                row.append(word.initial or '')
            if 'example' in fields:
                row.append(word.example or '')
            if 'grade' in fields:
                row.append(str(word.grade) if word.grade else '')
            if 'source' in fields:
                row.append(word.source or '')
            
            table_data.append(row)
        
        # 테이블 생성
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'HYGothic-Medium'),  # 헤더 한글 폰트
            ('FONTNAME', (0, 1), (-1, -1), 'HYSMyeongJo-Medium'),  # 본문 한글 폰트
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        
        story.append(table)
        
        # PDF 빌드
        doc.build(story)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'vocabulary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 단어 삭제 API
@app.route('/api/words/<int:word_id>', methods=['DELETE'])
def delete_word(word_id):
    try:
        word = Word.query.get_or_404(word_id)
        db.session.delete(word)
        db.session.commit()
        return jsonify({'success': True, 'message': '단어가 삭제되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# 통계 API
@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_words = Word.query.count()
        
        # 학년별 통계
        grade_stats = db.session.query(
            Word.grade,
            db.func.count(Word.id)
        ).group_by(Word.grade).all()
        
        # 출처별 통계
        source_stats = db.session.query(
            Word.source,
            db.func.count(Word.id)
        ).group_by(Word.source).all()
        
        return jsonify({
            'total_words': total_words,
            'grade_stats': [{'grade': g, 'count': c} for g, c in grade_stats if g],
            'source_stats': [{'source': s, 'count': c} for s, c in source_stats if s]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 데이터베이스 초기화
    with app.app_context():
        try:
            # MySQL 연결 테스트
            db.engine.connect()
            print("[SUCCESS] MySQL database connected successfully.")
            print(f"   Server: {MYSQL_HOST}:{MYSQL_PORT}")
            print(f"   Database: {MYSQL_DATABASE}")
            print(f"   User: {MYSQL_USER}")
            
            # 테이블 생성
            db.create_all()
            print("[SUCCESS] Database tables created.")
            
            # 테이블 확인
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            if 'vocabulary_words' in tables:
                print("[SUCCESS] vocabulary_words table confirmed.")
            
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            print("\nFalling back to local SQLite...")
            # SQLite로 폴백
            basedir = os.path.abspath(os.path.dirname(__file__))
            app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "vocabulary.db")}'
            db.create_all()
            print("[SUCCESS] Using local SQLite database.")
    
    app.run(debug=True, port=5001)  # 기존 앱과 포트 충돌 방지