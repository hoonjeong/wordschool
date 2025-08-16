from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import json # JSON 파싱을 위해 임포트
import re # 정규 표현식 사용을 위해 임포트

app = Flask(__name__)
CORS(app) # 개발 단계에서만 CORS 허용. 실제 배포 시에는 특정 Origin만 허용하도록 설정하세요.

# --- Gemini API 키 설정 ---
# ⚠️ 중요: 여기에 발급받은 Gemini API 키를 직접 붙여넣으세요.
# 이 방법은 로컬 테스트용으로만 사용하고, 실제 배포 시에는 반드시 환경 변수 사용을 권장합니다.
GEMINI_API_KEY = ""


genai.configure(api_key=GEMINI_API_KEY)
# --------------------------

# 1단계 페이지 렌더링
@app.route('/')
def index():
    return render_template('index.html')

# 2단계 페이지 렌더링 (POST 요청으로 지문 받음)
@app.route('/step2', methods=['GET', 'POST'])
def step2():
    # step2.html은 클라이언트 측 JavaScript에서 localStorage를 통해 지문 내용을 가져옵니다.
    return render_template('step2.html')

# 지문 분석 API 엔드포인트 (2단계 핵심 문단 분석에 사용)
@app.route('/analyze_passage', methods=['POST'])
def analyze_passage():
    data = request.get_json()
    passage_text = data.get('passage', '')

    if not passage_text:
        return jsonify({"error": "No passage text provided"}), 400

    # 문단 분리 로직: 연속된 두 줄바꿈으로 문단 구분하고, 빈 문단은 제거
    paragraphs = [p.strip() for p in passage_text.split('\n\n') if p.strip()]
    
    ai_recommended_index = -1 # AI 추천 인덱스 초기화
    ai_recommendation_reason = "AI가 핵심 문단을 분석하고 있습니다..." # 초기 로딩 메시지

    if not paragraphs:
        return jsonify({
            "paragraphs": [],
            "ai_recommended_main_paragraph_index": -1,
            "ai_recommendation_reason": "분석할 문단이 없습니다."
        })

    try:
        model = genai.GenerativeModel('gemini-2.5-pro') # Gemini Pro 모델 사용

        # 1. 핵심 문단 번호 추천 프롬프트
        paragraph_list_for_prompt = ""
        for i, p in enumerate(paragraphs):
            paragraph_list_for_prompt += f"[{i}] {p}\n"  # 내부적으로는 0부터 시작하는 인덱스 사용

        prompt_indices = (
            "다음 지문의 각 문단을 읽고, 전체 지문의 핵심 내용을 가장 잘 담고 있는 문단(들)의 인덱스 번호(0부터 시작)를 추천해줘. "
            "만약 여러 문단이 중요하다면 모두 포함해줘. "
            "추천하는 인덱스 번호 외에 다른 내용은 일절 포함하지 말고, 순수한 JSON 배열 형태로만 출력해줘.\n\n"
            f"{paragraph_list_for_prompt}"
        )
        
        response_indices = model.generate_content(prompt_indices)
        
        # AI 응답 파싱 (JSON 또는 텍스트에서 숫자 추출)
        ai_output_indices = response_indices.text.strip()
        
        try:
            recommended_indices_list = json.loads(ai_output_indices)
            if isinstance(recommended_indices_list, list) and all(isinstance(x, int) for x in recommended_indices_list):
                if recommended_indices_list:
                    ai_recommended_index = recommended_indices_list[0] # 여러 개 추천 시 첫 번째 사용
            else:
                raise ValueError("AI response for indices is not a valid list of integers.")
        except (json.JSONDecodeError, ValueError):
            numbers = re.findall(r'\d+', ai_output_indices)
            if numbers:
                ai_recommended_index = int(numbers[0])
            else:
                print(f"경고: AI 응답에서 유효한 핵심 문단 인덱스를 찾을 수 없습니다: {ai_output_indices}")
                ai_recommended_index = -1 # 찾지 못하면 -1로 설정

        # 2. 핵심 문단 추천 이유 프롬프트 (핵심 문단이 존재할 경우에만 호출)
        if ai_recommended_index != -1 and ai_recommended_index < len(paragraphs):
            # 사용자에게 보여지는 번호는 1부터 시작 (인덱스 + 1)
            display_number = ai_recommended_index + 1
            reason_prompt = (
                f"다음 지문에서 {display_number}번 문단을 핵심 문단으로 추천한 이유를 1문장으로 간결하게 설명해줘.\n\n"
                f"지문:\n{paragraph_list_for_prompt}"
            )
            reason_response = model.generate_content(reason_prompt)
            ai_recommendation_reason = reason_response.text.strip()
            
            # AI 응답에서 불필요한 서두 제거 (예: "[0] 이 문단은 ~" 또는 "1번 문단은 ~" 와 같이 올 수 있음)
            if ai_recommendation_reason.startswith(f"[{ai_recommended_index}]"):
                ai_recommendation_reason = ai_recommendation_reason.split(']', 1)[1].strip()
            elif ai_recommendation_reason.startswith(f"{display_number}번"):
                # "1번 문단은" 같은 패턴 제거
                ai_recommendation_reason = ai_recommendation_reason.replace(f"{display_number}번 문단은", "").replace(f"{display_number}번 문단이", "").strip()
            # AI가 번호 언급 없이 바로 이유를 말하면 그대로 사용
            
        else:
            ai_recommendation_reason = "AI가 핵심 문단을 분석 중이거나 추천할 수 없습니다."


    except Exception as e:
        print(f"Gemini API 호출 중 오류 발생: {e}")
        ai_recommended_index = -1 # 오류 시 AI 추천 없음
        ai_recommendation_reason = "AI 추천 실패: 모델 호출 중 오류 발생"

    return jsonify({
        "paragraphs": paragraphs,
        "ai_recommended_main_paragraph_index": ai_recommended_index,
        "ai_recommendation_reason": ai_recommendation_reason
    })

if __name__ == '__main__':
    # 개발 모드: 코드 변경 시 자동 재시작.
    # Flask 서버는 기본적으로 http://127.0.0.1:5000/ 에서 실행됩니다.
    if GEMINI_API_KEY == "" or not GEMINI_API_KEY:
        print("\n--- 경고 ---")
        print("GEMINI_API_KEY가 설정되지 않았거나 기본값으로 되어 있습니다.")
        print("app.py 파일 내 GEMINI_API_KEY 변수에 발급받은 실제 API 키를 붙여넣으세요.")
        print("이 방식은 로컬 테스트용으로만 사용해야 하며, 실제 배포 시에는 환경 변수 사용을 권장합니다.")
        print("----------\n")
    
    app.run(debug=True)