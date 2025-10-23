from fastapi import FastAPI, Response
import httpx, os

app = FastAPI(title='TV Proxy')
COOKIE = os.getenv('TRADINGVIEW_COOKIES', '')

@app.get('/tv/forward')
async def forward(url: str):
    if not url:
        return Response(content='Missing url', status_code=400)
    headers = {'User-Agent': 'Mozilla/5.0', 'Cookie': COOKIE}
    async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
        r = await client.get(url, headers=headers)
        return Response(content=r.text, media_type='text/html', status_code=r.status_code)
