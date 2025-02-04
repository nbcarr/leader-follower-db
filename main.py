from fastapi import FastAPI
import asyncio
from aiofile import AIOFile
import time
import json

class Cache:
    def __init__(self):
        self.cache = {}

    def _is_expired(self, k: str):
        item = self.cache.get(k)
        return item and time.time() > item['expires_at']

    def get(self, k: str):
        if k not in self.cache or self._is_expired(k):
            return {"k": k, "v": None}
        return {"k": k, "v": self.cache[k]['value']}

    def put(self, k: str, v: str, ttl: int = 86400):
        self.cache[k] = {'value': v, 'expires_at': time.time() + ttl}
        return {"result": "success"}

    def delete(self, k: str):
        return {"result": "success" if self.cache.pop(k, None) else "key not found"}

    def cleanup(self):
        expired_keys = [k for k, v in self.cache.items() if time.time() > v['expires_at']]
        for key in expired_keys:
            del self.cache[key]

    async def persist(self):
        async with AIOFile("db.json", "w") as afp:
            await afp.write(json.dumps(self.cache))

    async def load(self):
        try:
            async with AIOFile("db.json", "r") as afp:
                data = await afp.read()
                if data:
                    self.cache = json.loads(data)
        except FileNotFoundError:
                pass

cache = Cache()

async def lifespan(app: FastAPI):
    await cache.load()

    async def cleanup_task():
        while True:
            await asyncio.sleep(60)
            cache.cleanup()

    async def persist_task():
        while True:
            await asyncio.sleep(60)
            await cache.persist()

    cleanup_task = asyncio.create_task(cleanup_task())
    persist_task = asyncio.create_task(persist_task())

    yield
    cleanup_task.cancel()
    persist_task.cancel()

app = FastAPI(lifespan=lifespan)

@app.get("/get")
async def handle_get(k: str):
    return cache.get(k)

@app.post("/put")
async def handle_post(k: str, v: str):
    return cache.put(k, v)

@app.post("/delete")
async def handle_delete(k: str):
    return cache.delete(k)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
