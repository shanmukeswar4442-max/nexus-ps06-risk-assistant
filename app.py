import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="Transaction Risk Investigation Assistant",
    description="NexusTiq24 Track PS06 Submission",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "message": "Transaction Risk Investigation Assistant API is running",
        "track_id": "PS06"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
