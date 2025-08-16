from fastapi import FastAPI
from .routers import youtube, text, web

app = FastAPI(title="TruthLens API", version="0.1.0")

@app.get("/")
def root():
    return {"name": "TruthLens", "ok": True}

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(text.router)
app.include_router(youtube.router)
app.include_router(web.router)


