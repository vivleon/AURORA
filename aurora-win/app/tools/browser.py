# app/tools/browser.py
# (requirements.txt에 'playwright' 필요)
from playwright.async_api import async_playwright
import asyncio

async def search(args, policy, db):
    """
    Playwright를 사용하여 웹페이지를 스크랩하고 텍스트를 반환합니다.
    (index.html [cite: vivleon/aurora/AURORA-main/index.html] sec 1.3, 3.3 기능)
    """
    query = args.get("query", "https_example_com") # URL 또는 검색어
    url = query if query.startswith("http") else f"https://www.google.com/search?q={query}"
    
    print(f"[Tool.Browser] Navigating to: {url}")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=10000)
            
            # 페이지의 메인 콘텐츠 텍스트 추출 (간단한 예시)
            # (RAG/요약을 위해 BeautifulSoup4 또는 Jina Reader 사용 권장)
            content = await page.evaluate('''() => {
                const readabilityScript = document.createElement('script');
                readabilityScript.src = 'https://cdn.jsdelivr.net/npm/@mozilla/readability@0.5.0/Readability.js';
                document.head.appendChild(readabilityScript);
                
                return new Promise((resolve) => {
                    readabilityScript.onload = () => {
                        const reader = new Readability(document.cloneNode(true));
                        const article = reader.parse();
                        resolve(article ? article.textContent : document.body.innerText.substring(0, 5000));
                    };
                    setTimeout(() => resolve(document.body.innerText.substring(0, 5000)), 1000);
                });
            }''')
            
            await browser.close()
            
            summary = (content or "").strip()
            print(f"[Tool.Browser] Scraped {len(summary)} chars.")
            return {"sources": [url], "summary": summary[:5000]} # 5000자 제한
            
    except Exception as e:
        print(f"[Tool.Browser ERROR] Playwright failed: {e}")
        return {"sources": [url], "summary": None, "error": str(e)}