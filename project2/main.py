import os
import time
import sys # 추가
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from google import genai
except ImportError:
    print("[오류] google-genai 라이브러리가 설치되지 않았습니다. requirements.txt를 확인하세요.")
    sys.exit(1)

# 1. API 키 및 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send_email(subject, body_html):
    sender_email = os.environ.get('SENDER_EMAIL', '')
    sender_password = os.environ.get('SENDER_PASSWORD', '')
    receiver_email = os.environ.get('RECEIVER_EMAIL', '')

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
        print("[Project 2] GEMINI_API_KEY가 설정되지 않았습니다. GitHub Secrets를 확인하세요.")
        sys.exit(1)

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # 2. 동영상 파일 경로 설정
    # GitHub Actions에서는 레포지토리 루트 기준 project2/data 폴더에서 읽어옵니다.
    data_dir = os.path.join('project2', 'data')
    
    if not os.path.exists(data_dir):
        print(f"[Project 2] 에러: '{data_dir}' 폴더를 찾을 수 없습니다.")
        sys.exit(1)

    # 대소문자 구분 없이 .mp4 파일을 찾습니다.
    video_files = [f for f in os.listdir(data_dir) if f.lower().endswith('.mp4')]
    
    if not video_files:
        print(f"[Project 2] '{data_dir}' 폴더에 mp4 파일이 없습니다.")
        sys.exit(1)

    video_path = os.path.join(data_dir, video_files[0])
    video_file_obj = None

    try:
        print(f"[{video_files[0]}] 업로드 및 분석 시작...")
        video_file_obj = client.files.upload(file=video_path)
        
        while video_file_obj.state.name == "PROCESSING":
            time.sleep(5)
            video_file_obj = client.files.get(name=video_file_obj.name)
        
        if video_file_obj.state.name == "FAILED":
            raise ValueError("Google 서버에서 동영상 처리에 실패했습니다.")

        model_id = "gemini-2.5-flash" 
        prompt = "이 동영상에서 인물이 어떤 행동을 하고 있는지 시간 흐름에 따라 상세히 분석해줘."

        response = client.models.generate_content(
            model=model_id,
            contents=[video_file_obj, prompt]
        )

        analysis_result = response.text
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: sans-serif; line-height: 1.6; color: #333; padding: 20px; }}
                .result-box {{ background: #f9f9f9; padding: 20px; border-radius: 8px; border-left: 5px solid #4CAF50; white-space: pre-wrap; }}
            </style>
        </head>
        <body>
            <h2>🎥 Gemini 동영상 동작 분석 보고서</h2>
            <p><b>분석 파일:</b> {video_files[0]}</p>
            <div class="result-box">{analysis_result}</div>
            <br>
            <p>본 메일은 GitHub Actions를 통해 자동으로 발송되었습니다.</p>
        </body>
        </html>
        """
        
        send_email(f"[Gemini 분석] {video_files[0]} 행동 분석 결과", html_body)
        print("모든 작업이 완료되었습니다.")

    except Exception as e:
        print(f"[에러 발생] {e}")
        sys.exit(1)
    finally:
        if video_file_obj:
            try:
                client.files.delete(name=video_file_obj.name)
                print("임시 파일 삭제 완료")
            except:
                pass

if __name__ == "__main__":
    main()
