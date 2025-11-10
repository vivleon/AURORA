# app/core/smart_inbox.py
from typing import Dict, Any, List
from app.tools import mail, nlp
from app.memory.store import DB

async def process_inbox(
    policy, 
    db: DB, 
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Smart Inbox 워크플로우를 실행합니다.
    1. 메일 목록(list)을 가져옵니다.
    2. 각 메일의 본문(get)을 가져옵니다.
    3. 본문을 분류(classify)하고 요약(summarize)합니다.
    4. '중요' 또는 '일반' 메일의 경우 초안(compose)을 생성합니다.
    """
    print(f"[SmartInbox] Processing started (limit={limit})...")
    
    # 1. 메일 목록 가져오기
    try:
        list_result = await mail.list({}, policy, db)
        emails = list_result.get("emails", [])[:limit]
    except Exception as e:
        print(f"[SmartInbox ERROR] Failed to list mail: {e}")
        return [{"error": "Failed to list mail", "detail": str(e)}]

    results = []

    for email_header in emails:
        email_id = email_header.get("id")
        if not email_id:
            continue
            
        try:
            # 2. 메일 본문 가져오기
            email_body_result = await mail.get({"id": email_id}, policy, db)
            body = email_body_result.get("body", "")
            if not body:
                continue

            # 3. 분류 (LLM 호출)
            categories = ["중요", "일반", "스팸", "뉴스레터"]
            classify_result = await nlp.classify({"text": body, "categories": categories}, policy, db)
            category = classify_result.get("category", "일반")

            # 4. '스팸' 또는 '뉴스레터'는 건너뛰기
            if category in ["스팸", "뉴스레터"]:
                results.append({"id": email_id, "status": "skipped", "category": category})
                continue

            # 5. 요약 (LLM 호출)
            summarize_result = await nlp.summarize({"text": body, "style": "3줄 요약"}, policy, db)
            summary = summarize_result.get("summary", "")

            # 6. 초안 작성 (내부 호출)
            draft_subject = f"[요약: {category}] {email_header.get('subject')}"
            draft_body = f"--- 원본 메일 요약 ---\n{summary}\n\n--- 원본 ---\n{body}"
            
            draft_result = await mail.compose({
                "subject": draft_subject,
                "body": draft_body,
                "to": ["draft@local.host"] # 초안함으로
            }, policy, db)

            results.append({
                "id": email_id, 
                "status": "processed", 
                "category": category, 
                "summary": summary,
                "draft_id": draft_result.get("subject") # 간단한 예시 ID
            })
            
        except Exception as e:
            print(f"[SmartInbox ERROR] Failed to process email {email_id}: {e}")
            results.append({"id": email_id, "status": "error", "detail": str(e)})

    print(f"[SmartInbox] Processing finished. {len(results)} emails processed.")
    return results