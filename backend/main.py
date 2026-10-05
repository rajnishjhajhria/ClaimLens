import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ai_check import AiCheckError, ai_check, cached as ai_cached
from pipeline import check_forward

app = FastAPI(title="ClaimLens")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class CheckRequest(BaseModel):
    text: str = Field(min_length=5, max_length=3000)


class AiCheckRequest(BaseModel):
    claim: str = Field(min_length=5, max_length=600)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/check")
def check(req: CheckRequest):
    try:
        return check_forward(req.text.strip())
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy right now. Please try again in a minute.",
        )


ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024


@app.post("/check-image")
def check_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Please upload a PNG, JPG or WebP image.")
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image is larger than 5 MB.")
    try:
        return check_forward(image=data, mime=file.content_type)
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy right now. Please try again in a minute.",
        )


# ---------- optional AI check (not a fact-check) ----------
class RateLimiter:
    """Allow `limit` calls per `window` seconds for each client address."""

    def __init__(self, limit=5, window=60):
        self.limit, self.window = limit, window
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, who):
        now = time.time()
        with self.lock:
            q = self.hits[who]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return int(self.window - (now - q[0])) + 1  # seconds to wait
            q.append(now)
            return 0


ai_limiter = RateLimiter(limit=5, window=60)
AI_ERROR_STATUS = {"quota": 429, "busy": 503, "failed": 502}


@app.post("/ai-check")
def ai_check_endpoint(req: AiCheckRequest, request: Request):
    """Runs only when the person clicks the button. Cached answers do not count against the limit."""
    claim = req.claim.strip()
    hit = ai_cached(claim)
    if hit:
        return hit
    who = request.client.host if request.client else "unknown"
    wait = ai_limiter.check(who)
    if wait:
        raise HTTPException(
            status_code=429,
            detail=f"Too many AI checks in a short time. Try again in {wait} seconds.",
            headers={"Retry-After": str(wait)},
        )
    try:
        return ai_check(claim)
    except AiCheckError as e:
        raise HTTPException(status_code=AI_ERROR_STATUS.get(e.kind, 502), detail=e.message)