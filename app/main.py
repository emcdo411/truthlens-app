from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .routers import youtube, text, web
from .utils.rate_limit import TokenBucket

app = FastAPI(title="TruthLens", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

bucket = TokenBucket(rate=10, per_seconds=60)  # 10 req/min (demo)

@app.middleware("http")
async def throttle(request: Request, call_next):
    if not bucket.allow():
        from fastapi.responses import JSONResponse
        return JSONResponse({"detail": "Rate limit"}, status_code=429)
    return await call_next(request)

app.include_router(youtube.router)
app.include_router(text.router)
app.include_router(web.router)
