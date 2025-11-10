async def summarize(args, policy, db):
    # TODO: 로컬 LLM 또는 외부 API를 통한 요약
    return {"summary": f"summary of: {args.get('text', '')[:20]}..."}