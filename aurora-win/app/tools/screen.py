# app/tools/screen.py
# (requirements.txt에 'pytesseract'와 'Pillow' 필요)

import os
import asyncio

try:
    import pytesseract
    from PIL import ImageGrab
except ImportError:
    print("[WARN] 'pytesseract' or 'Pillow' not installed. OCR tool will fail. (pip install pytesseract Pillow)")
    pytesseract = None
    ImageGrab = None

async def ocr(args, policy, db):
    """
    현재 화면을 캡처하여 OCR을 수행합니다. (비동기 처리)
    (README.md [cite: vivleon/aurora/AURORA-main/aurora-win/README.md]의 TESSERACT_PATH 설정 필요)
    """
    if not pytesseract or not ImageGrab:
        return {"text": None, "error": "Pytesseract or Pillow not installed"}

    print(f"[Tool.Screen] Performing Screen OCR...")
    
    tesseract_path = os.getenv("TESSERACT_PATH")
    if not tesseract_path:
        print("[WARN] TESSERACT_PATH not set. OCR tool will fail.")
        return {"text": None, "error": "TESSERACT_PATH not set"}
        
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    try:
        # 화면 캡처 (I/O 작업)
        img = await asyncio.to_thread(ImageGrab.grab)
        
        # OCR (CPU-bound 작업)
        # (TESSDATA_PREFIX 환경 변수가 설정되어 있어야 'kor' 사용 가능)
        lang = args.get("lang", "kor+eng")
        text = await asyncio.to_thread(pytesseract.image_to_string, img, lang=lang)
        
        print(f"[Tool.Screen] OCR extracted {len(text)} chars.")
        return {"text": text}
        
    except Exception as e:
        print(f"[Tool.Screen ERROR] OCR failed: {e}")
        return {"text": None, "error": str(e)}