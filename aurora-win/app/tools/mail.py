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

# [신규] Helper function to parse subject from .eml files (간단한 파싱)
def _parse_subject_from_eml(filepath: Path) -> str:
    try:
        # Simplistic parsing: just read the first few lines to find 'Subject:'
        content = filepath.read_text('utf-8', errors='ignore')
        for line in content.splitlines():
            if line.lower().startswith("subject:"):
                return line[8:].strip()
        return "[No Subject]"
    except Exception:
        return "[Parsing Error]"


async def list(args, policy, db):
    """
    [업그레이드]
    INBOX_PATH에서 실제 .eml 파일 목록을 가져옵니다. (하드코딩 제거)
    """
    if not INBOX_PATH.exists():
        INBOX_PATH.mkdir(parents=True, exist_ok=True)

    emails = []
    # [HARDCODING REMOVAL] 실제 파일 시스템에서 .eml 파일을 읽습니다.
    for i, filepath in enumerate(INBOX_PATH.glob("*.eml")):
        if i >= args.get("limit", 10): # 기본 10개로 제한
            break
        
        # 파일 이름을 ID로 사용
        msg_id = filepath.stem
        subject = _parse_subject_from_eml(filepath)
        
        emails.append({
            "id": msg_id, 
            "subject": subject, 
            "from": "inbox_user@local.host", # 발신자 정보 파싱은 스텁 유지
            "filepath": str(filepath)
        })

    print(f"[Tool.Mail] Listing {len(emails)} emails from {INBOX_PATH}")
    return {"emails": emails}

async def get(args, policy, db):
    """
    [업그레이드]
    특정 이메일 ID의 본문을 실제 파일에서 가져옵니다. (하드코딩 제거)
    """
    msg_id = args.get("id")
    if not msg_id:
        raise ValueError("Email 'id' is required")
    
    # [HARDCODING REMOVAL] 파일 시스템에서 직접 파일을 읽습니다.
    filepath = INBOX_PATH / f"{msg_id}.eml"
    if not filepath.exists():
        # 파일명을 못 찾을 경우, 확장자를 찾아서 대소문자 문제 해결 시도
        found_files = list(INBOX_PATH.glob(f"{msg_id}.*"))
        if found_files:
            filepath = found_files[0]
        else:
            raise FileNotFoundError(f"Email file not found for ID: {msg_id}")
    
    print(f"[Tool.Mail] Getting email content for: {filepath}")
    
    try:
        # 이메일 본문 전체를 읽습니다. 
        body = filepath.read_text('utf-8', errors='ignore')
        return {"id": msg_id, "body": body}
    except Exception as e:
        return {"id": msg_id, "body": f"[Error Reading File: {e}]"}