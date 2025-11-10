# app/tools/nlp.py
# index.html (sec 7. Routine Builder)에서 사용됨

async def summarize(args, policy, db):
    """
    텍스트를 요약합니다.
    (index.html, sec 15.3, 16.4 - 로컬 LLM 라우팅 필요)
    """
    text = args.get("text", "")
    style = args.get("style", "bullet-3")
    
    if not text:
        return {"summary": ""}

    print(f"[Tool] Summarizing text (style: {style})...")
    
    # TODO: app/router/model_router.json을 참조하여
    # 로컬 (e.g., phi3-mini) 또는 클라우드 LLM 호출
    
    summary = f"Summary of '{text[:20]}...' (style: {style})"
    return {"summary": summary}