import asyncio
import os
from aiohttp import web, ClientSession, ClientTimeout

async def _start_web():
    r = web.RouteTableDef()

    @r.get("/", allow_head=True)
    async def _root(req):
        return web.json_response({"status": "running", "bot": "tellycloudbots"})
    
    @r.get("/health", allow_head=True)
    async def _health(req):
        return web.json_response({"status": "healthy"})

    app = web.Application(client_max_size=30000000)
    app.add_routes(r)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"Web server started on port {port}")

async def _ping(url, interval):
    if not url:
        return
    
    await asyncio.sleep(60)
    
    while True:
        await asyncio.sleep(interval)
        try:
            async with ClientSession(timeout=ClientTimeout(total=10)) as s:
                async with s.get(url) as resp:
                    print(f"Pinged: {resp.status}")
        except:
            pass
