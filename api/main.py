from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="Multi-Cloud API")


@app.get("/")
async def root():
    """Root endpoint returning a simple JSON response"""
    return {"hi": "Hello from Multi-Cloud API!"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
