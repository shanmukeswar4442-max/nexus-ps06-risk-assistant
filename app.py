from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.routes import router as api_router

app = FastAPI(
    title="Transaction Risk Investigation Assistant",
    description="NexusTiq24 Track PS06 Submission",
    version="1.0.0"
)

# 1. Health check & status endpoints
@app.get("/ping")
def ping():
    return {"status": "pong", "track_id": "PS06"}

# 2. Register API router (/api/...)
app.include_router(api_router)

# 3. Mount static frontend directory AFTER all API routes
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
