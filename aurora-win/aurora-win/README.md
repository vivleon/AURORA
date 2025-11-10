python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
set TESSERACT_PATH=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload