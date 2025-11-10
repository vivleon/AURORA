# app/tools/nlp.py
# [수정] model_runner를 임포트하여 실제 LLM 추론을 호출합니다.

try:
    from app.router import model_runner
except ImportError:
    print("[ERROR] nlp.py: Failed to import model_runner. LLM calls will fail.")
    model_runner = None

async def summarize(args, policy, db):
    """
    텍스트를 요약합니다. (model_runner.py 호출)
    """
    text = args.get("text", "")
    style = args.get("style", "bullet-3")
    
    if not text:
        return {"summary": ""}

    print(f"[Tool] Summarizing text (style: {style})...")
    
    if not model_runner:
        return {"summary": f"[Stub] Summary of '{text[:20]}...'", "error": "model_runner not imported"}

    # model_runner를 통해 하이브리드 라우팅 (로컬/클라우드)
    prompt = f"다음 텍스트를 {style} 스타일로 요약해줘:\n\n{text}"
    
    result = await model_runner.run_inference(
        task="summarize",
        prompt=prompt,
        risk="low",
        max_tokens=256
    )
    
    if result.get("error"):
        return {"summary": None, "error": result["error"]}
        
    return {"summary": result.get("text"), "model": result.get("model")}

async def classify(args, policy, db):
    """
    텍스트를 분류합니다. (예: Smart Inbox)
    """
    text = args.get("text", "")
    categories = args.get("categories", ["중요", "스팸", "일반"])
    
    if not text:
        return {"category": None}
        
    print(f"[Tool] Classifying text...")

    if not model_runner:
        return {"category": "general", "error": "model_runner not imported"}

    prompt = f"다음 텍스트를 [{', '.join(categories)}] 중 하나로 분류해줘. 단어 하나로만 답해.\n\n{text}"
    
    result = await model_runner.run_inference(
        task="intent", # 'intent' 모델 사용
        prompt=prompt,
        risk="low",
        max_tokens=10
    )
    
    category = result.get("text", "general").strip()
    return {"category": category, "model": result.get("model")}