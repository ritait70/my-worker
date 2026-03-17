import os
import pandas as pd
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import sys

# 1. 데이터 로드 (상대 경로로 수정)
# GitHub Actions에서는 레포지토리 루트 기준 data/ 폴더에서 읽어옵니다.
data_dir = 'data'
train_file_path = os.path.join(data_dir, '2_PAproject_2_4_machine.csv')
predict_file_path = os.path.join(data_dir, '2_PAproject_2_4_machine_prediction.csv')

def send_email(subject, body_html):
    # 환경 변수에서 메일 설정 정보 가져오기
    sender_email = os.environ.get('SENDER_EMAIL')
    sender_password = os.environ.get('SENDER_PASSWORD')
    receiver_email = os.environ.get('RECEIVER_EMAIL')

    if not all([sender_email, sender_password, receiver_email]):
        print("이메일 설정 환경 변수가 누락되었습니다. 메일을 보내지 않습니다.")
        return

    # 메일 객체 생성
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # HTML 본문 추가
    message.attach(MIMEText(body_html, "html"))

    try:
        # SMTP 서버 연결 및 메일 발송 (Gmail 기준)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"이메일이 {receiver_email}로 성공적으로 발송되었습니다.")
    except Exception as e:
        print(f"이메일 발송 중 오류 발생: {e}")

def main():
    try:
        # 데이터 파일 존재 확인
        if not os.path.exists(train_file_path) or not os.path.exists(predict_file_path):
            print(f"데이터 파일을 찾을 수 없습니다. 경로를 확인하세요: {data_dir}")
            return

        df_train = pd.read_csv(train_file_path)
        df_predict = pd.read_csv(predict_file_path)
        print("학습 및 예측 데이터를 성공적으로 불러왔습니다.")

        # 2. 학습용 데이터 설정
        X_train = df_train[['Department', 'Performance_Rating', 'Salary', 'Work_Hours']]
        y_train = df_train['Left']

        # 3. 전처리 파이프라인 설정
        categorical_features = ['Department']
        numeric_features = ['Performance_Rating', 'Salary', 'Work_Hours']

        preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
            ])

        # 4. SVM 모델 구성
        svm_model = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('classifier', SVC(kernel='rbf', probability=True, random_state=42))
        ])

        # 5. 모델 학습
        svm_model.fit(X_train, y_train)
        print("모델 학습이 완료되었습니다.")

        # 6. 새로운 데이터에 대한 예측 수행
        X_new = df_predict[['Department', 'Performance_Rating', 'Salary', 'Work_Hours']]
        predictions = svm_model.predict(X_new)
        pred_probas = svm_model.predict_proba(X_new)

        # 7. 결과 결합
        df_predict['Predicted_Left'] = predictions
        df_predict['Left_Probability(%)'] = (pred_probas[:, 1] * 100).round(2)

        # 8. 결과 요약 및 이메일 본문 작성
        # 전체 예측 결과를 테이블로 포함합니다.
        full_results_df = df_predict[['Department', 'Salary', 'Predicted_Left', 'Left_Probability(%)']]
        
        # HTML 형식의 이메일 본문 구성
        html_body = f"""
        <html>
        <head>
            <style>
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h2>SVM 퇴사 예측 전체 결과 보고서</h2>
            <p>데이터가 업데이트되어 자동 분석이 수행되었습니다.</p>
            <h3>전체 예측 결과 (총 {len(df_predict)} 건)</h3>
            {full_results_df.to_html(index=False, classes='table')}
            <br>
            <p>본 메일은 GitHub Actions를 통해 자동으로 발송되었습니다.</p>
        </body>
        </html>
        """

        # 9. 이메일 발송
        send_email("[자동화 알림] 머신러닝 예측 결과 보고", html_body)

    except Exception as e:
        print(f"실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
