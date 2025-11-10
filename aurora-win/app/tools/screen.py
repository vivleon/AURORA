# app/tools/screen.py
# index.html (sec 1.4, 3.3)에 정의된 기능
# README.md의 TESSERACT_PATH 환경 변수 설정 필요

import os
# import pytesseract # requirements.txt에 포함됨
# from PIL import ImageGrab # PIL(Pillow)도 필요함 (requirements.txt에 추가 권장)

async def ocr(args, policy, db):
    """
    현재 화면을 캡처하여 OCR을 수행합니다.
    """
    print(f"[Tool] Performing Screen OCR...")
    
    # TODO: 실제 Tesseract OCR 로직 구현
    # tesseract_path = os.getenv("TESSERACT_PATH")
    # if not tesseract_path:
    #     print("[WARN] TESSERACT_PATH not set. OCR tool will fail.")
    #     return {"text": None, "error": "TESSERACT_PATH not set"}
    #
    # try:
    #     pytesseract.pytesseract.tesseract_cmd = tesseract_path
    #     img = ImageGrab.grab()
    #     text = pytesseract.image_to_string(img, lang='kor+eng') # 예: 한글+영어
    #     return {"text": text}
    # except Exception as e:
    #     return {"text": None, "error": str(e)}

    return {"text": "screen text placeholder (OCR not implemented)"}