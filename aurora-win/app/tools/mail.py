# app/tools/mail.py
import os
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Dict, Any

# [신규] 로컬 파일 시스템 경로 정의
MAIL_ROOT = Path(os.getenv("MAIL_ROOT", "data/mail"))
DRAFT_PATH = MAIL_ROOT / "drafts"
SENT_PATH = MAIL_ROOT / "sent"
INBOX_PATH = MAIL_ROOT / "inbox" # Smart Inbox용 (list/get)

# 디렉터리 생성
DRAFT_PATH.mkdir(parents=True, exist_ok=True)
SENT_PATH.mkdir(parents=True, exist_ok=True)
INBOX_PATH.mkdir(parents=True, exist_ok=True)

async def compose(args: Dict[str, Any], policy, db):
    """
    [업그레이드]
    메일 초안을 SMTP가 아닌 로컬 'data/mail/drafts/' 폴더에 .eml 파일로 저장합니다.
    """
    subject = args.get("subject", "No Subject")
    body = args.get("body", "")
    to = args.get("to", ["draft@local.host"])
    
    print(f"[Tool.Mail] Composing draft to file system: {subject}")

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = os.getenv("SMTP_USER", "aurora@local.host") # .env 값 재사용 (없으면 폴백)
    msg['To'] = ", ".join(to)

    # 파일명 생성
    safe_subject = "".join(c for c in subject if c.isalnum() or c in " -_").strip()[:50]
    filename = f"draft_{int(time.time())}_{safe_subject}.eml"
    filepath = DRAFT_PATH / filename

    try:
        # [수정] aiofiles 대신 동기 I/O 사용 (asyncio.to_thread로 실행 권장)
        # 여기서는 간결성을 위해 동기 I/O를 직접 사용합니다.
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(msg))
        
        return {"draft": True, "subject": subject, "path": str(filepath)}
    except IOError as e:
        return {"draft": False, "error": str(e)}

async def send(args: Dict[str, Any], policy, db):
    """
    ! HIGH-RISK !
    [업그레이드]
    SMTP 대신, 메일을 로컬 'data/mail/sent/' 폴더에 .eml 파일로 "전송" (저장)합니다.
    """
    subject = args.get("subject", "No Subject")
    body = args.get("body", "No Body")
    to_list = args.get("to", [])
    
    if not to_list:
        raise ValueError("'to' field is required to send mail")

    print(f"[Tool.Mail] 'Sending' email to file system (sent/)...")

    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = os.getenv("SMTP_USER", "aurora@local.host")
    msg['To'] = ", ".join(to_list)

    # 파일명 생성
    filename = f"sent_{int(time.time())}.eml"
    filepath = SENT_PATH / filename

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(msg))
        
        print(f"[Tool.Mail] Email 'sent' to: {filepath}")
        return {"sent": True, "subject": subject, "path": str(filepath)}
        
    except IOError as e:
        print(f"[Tool.Mail ERROR] File write failed: {e}")
        return {"sent": False, "error": str(e)}

async def list(args, policy, db):
    """
    (Smart Inbox용 스텁)
    INBOX에서 '읽지 않은' 메일 목록을 가져옵니다.
    (실제 구현: INBOX_PATH에서 .eml 파일 파싱)
    """
    print(f"[Tool.Mail] Listing unread emails from {INBOX_PATH} (stub)")
    # 실제 구현: os.listdir(INBOX_PATH) 후 .eml 헤더 파싱
    # (스텁 유지)
    return {
        "emails": [
            {"id": "msg-123", "subject": "긴급: 4분기 실적 보고서", "from": "finance@example.com"},
            {"id": "msg-124", "subject": "뉴스레터: AI 최신 동향", "from": "newsletter@tech.com"},
            {"id": "msg-125", "subject": "회의 초대: 주간 싱크업", "from": "teammate@example.com"},
        ]
    }

async def get(args, policy, db):
    """
    (Smart Inbox용 스텁)
    특정 이메일 ID의 본문을 가져옵니다.
    (실제 구현: INBOX_PATH에서 {id}.eml 파일 파싱)
    """
    msg_id = args.get("id")
    if not msg_id:
        raise ValueError("Email 'id' is required")
    
    print(f"[Tool.Mail] Getting email content for: {msg_id} (stub)")
    # 실제 구현: (INBOX_PATH / f"{msg_id}.eml").read_text()
    
    # (스텁 유지)
    stub_bodies = {
        "msg-123": "CEO님, 4분기 실적 보고서 초안입니다. 검토 부탁드립니다...",
        "msg-124": "지난 주 AI 업계의 가장 큰 뉴스는...",
        "msg-125": "주간 싱크업 일정을 다음 주 월요일로 변경합니다...",
    }
    
    return {
        "id": msg_id,
        "body": stub_bodies.get(msg_id, "메일 본문을 찾을 수 없습니다.")
    }
