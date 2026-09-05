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

# Register API routes
app.include_router(api_router)

# Mount static frontend directory if present
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


@app.get("/ping")
def ping():
    return {"status": "pong", "track_id": "PS06"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
