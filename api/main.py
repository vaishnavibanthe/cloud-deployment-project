# main.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Multi-Cloud API")


@app.get("/")
async def root():
    """Root endpoint returning a simple JSON response"""
    return {"hi": "Hello from Multi-Cloud API!"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# Lambda handler using Mangum (safe to import in Lambda)
# Note: this requires `mangum` in requirements.txt
try:
    from mangum import Mangum  # optional import; only used in Lambda
    handler = Mangum(app)
except Exception:
    # If Mangum is not installed in local dev image, just ignore.
    handler = None


if __name__ == "__main__":
    # local development entrypoint (uvicorn)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
