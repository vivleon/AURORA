# app/tools/nlp.py
import asyncio
from typing import Dict, Any

try:
    from app.router import model_runner
except ImportError:
    print("[ERROR] nlp.py: Failed to import model_runner. LLM calls will fail.")
    model_runner = None

async def summarize(args, policy, db):
    text = args.get("text", "")
    style = args.get("style", "bullet-3")
    
    if not text:
        return {"summary": f"[INFO] No text provided for summary. Returning no-op.", "model": None}

    print(f"[Tool] Summarizing text (style: {style})...")
    
    if not model_runner:
        return {"summary": f"[Stub] Summary of '{text[:20]}...'", "error": "model_runner not imported"}

    prompt = f"다음 텍스트를 {style} 스타일로 요약해줘:\n\n{text}"
    
    result = await model_runner.run_inference(
        task="summarize",
        prompt=prompt,
        risk="low",
        max_tokens=256
    )
    
    summary_text = result.get("text")
    if result.get("error") or not summary_text or summary_text.strip() == "":
        # [FIX] 빈 응답일 때 오류 반환
        return {"summary": "[ERROR] LLM returned empty response or inference failed.", "error": result.get("error") or "Empty LLM Output"}

    return {"summary": summary_text, "model": result.get("model")}

async def classify(args, policy, db):
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
    
    category_text = result.get("text")
    category = "general"
    if category_text:
        category = category_text.strip()
        
    return {"category": category, "model": result.get("model")}