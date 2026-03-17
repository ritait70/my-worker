import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google import genai

# 1. API 키 및 설정 (GitHub Secrets에서 가져옴)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send_email(subject, body_html):
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    receiver_email = os.environ.get('RECEIVER_EMAIL')

    if not all([sender_email, sender_password, receiver_email]):
        print("[Project 2] 이메일 설정 환경 변수가 누락되었습니다.")
        return

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print("[Project 2] 이메일 발송 성공")
    except Exception as e:
        print(f"[Project 2] 이메일 발송 실패: {e}")

def main():
    if not GEMINI_API_KEY:
        print("[Project 2] GEMINI_API_KEY가 설정되지 않았습니다.")
        return

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 2. 동영상 파일 경로 설정 (project2/data 폴더 내 모든 mp4 파일 대상)
    data_dir = os.path.join('project2', 'data')
    video_files = [f for f in os.listdir(data_dir) if f.endswith('.mp4')]
    
    if not video_files:
        print("[Project 2] 분석할 mp4 동영상 파일이 data 폴더에 없습니다.")
        return

    # 가장 최근에 추가된 하나의 파일만 분석하는 예시
    video_path = os.path.join(data_dir, video_files[0])
    video_file_obj = None

    try:
        print(f"[{video_files[0]}] 업로드 중...")
        video_file_obj = client.files.upload(file=video_path)
        
        print("Google 서버에서 동영상을 처리 중입니다...")
        while video_file_obj.state.name == "PROCESSING":
            time.sleep(5)
            video_file_obj = client.files.get(name=video_file_obj.name)
        
        if video_file_obj.state.name == "FAILED":
            raise ValueError("동영상 처리에 실패했습니다.")

        # 3. AI 분석 요청
        model_id = "gemini-2.0-flash" # 최신 안정화 모델
        prompt = "이 동영상에서 인물이 어떤 행동을 하고 있는지 시간 흐름에 따라 상세히 분석해줘."

        print(f"AI 분석 중 ({model_id})...")
        response = client.models.generate_content(
            model=model_id,
            contents=[video_file_obj, prompt]
        )

        # 4. 결과 이메일 발송
        analysis_result = response.text
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; line-height: 1.6; color: #333; }}
                .result-box {{ background: #f4f4f4; padding: 20px; border-radius: 8px; border-left: 5px solid #4CAF50; }}
            </style>
        </head>
        <body>
            <h2>🎥 Gemini 동영상 동작 분석 보고서</h2>
            <p><b>분석 파일:</b> {video_files[0]}</p>
            <div class="result-box">
                {analysis_result.replace('\n', '<br>')}
            </div>
            <br>
            <p>본 메일은 GitHub Actions를 통해 자동으로 발송되었습니다.</p>
        </body>
        </html>
        """
        
        send_email(f"[Gemini 분석] {video_files[0]} 행동 분석 결과", html_body)

    except Exception as e:
        print(f"분석 중 오류 발생: {e}")
    finally:
        if video_file_obj:
            client.files.delete(name=video_file_obj.name)
            print("임시 파일 삭제 완료")

if __name__ == "__main__":
    main()
