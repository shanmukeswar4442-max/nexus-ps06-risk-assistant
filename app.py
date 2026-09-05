import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="Production Transaction Risk Investigation Assistant",
    description="NexusTiq24 Track PS06 Submission",
    version="2.0.0"
)

@app.get("/ping")
def ping():
    return {"status": "pong", "track_id": "PS06"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
