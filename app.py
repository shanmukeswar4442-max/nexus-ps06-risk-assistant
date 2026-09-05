from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.core.config import settings
from src.core.logging_config import logger
from src.api.routes import router as api_router

app = FastAPI(
    title=settings.APP_NAME,
    description=f"NexusTiq24 Track {settings.TRACK_ID} Submission",
    version="2.0.0"
)

@app.get("/ping")
def ping():
    return {"status": "pong", "track_id": settings.TRACK_ID}

# Register API routes FIRST
app.include_router(api_router)

# Mount static frontend directory AFTER API routes
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")

if __name__ == "__main__":
    logger.info(f"Starting {settings.APP_NAME} on http://{settings.HOST}:{settings.PORT}")
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=False)
