# app/tools/mail.py
# (requirements.txt에 'python-dotenv' 필요)
import smtplib
import os
from email.message import EmailMessage

# .env 파일에서 SMTP 설정 로드 (보안)
# (예: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
# os.load_dotenv() # main.py에서 이미 로드됨

async def compose(args, policy, db):
    """
    메일 초안을 생성합니다 (실제 발송은 'send' op).
    """
    subject = args.get("subject", "No Subject")
    body = args.get("body", "")
    to = args.get("to", ["draft@local.host"])
    
    print(f"[Tool.Mail] Composing draft: {subject}")
    # TODO: 'drafts' 폴더나 DB에 임시 저장
    
    return {"draft": True, "subject": subject, "to": to}

async def send(args, policy, db):
    """
    ! HIGH-RISK !
    SMTP를 통해 실제 메일을 발송합니다.
    (planner_consent_gate [cite: vivleon/aurora/AURORA-main/aurora-win/app/core/planner_consent_gate.py]에서 'mail.send'는 고위험)
    """
    subject = args.get("subject", "No Subject")
    body = args.get("body", "No Body")
    to_list = args.get("to", [])
    
    if not to_list:
        raise ValueError("'to' field is required to send mail")

    # .env에서 SMTP 설정 가져오기
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")

    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS]):
        print("[Tool.Mail ERROR] SMTP settings (HOST, USER, PASS) not found in .env")
        return {"sent": False, "error": "SMTP configuration missing"}

    print(f"[Tool.Mail] Sending email via {SMTP_HOST}:{SMTP_PORT}...")

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(to_list)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.starttls() # TLS 암호화
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
        
        print(f"[Tool.Mail] Email sent to: {to_list}")
        return {"sent": True, "subject": subject}
        
    except smtplib.SMTPException as e:
        print(f"[Tool.Mail ERROR] SMTP failed: {e}")
        return {"sent": False, "error": str(e)}