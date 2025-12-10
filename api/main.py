# main.py
from fastapi import FastAPI

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
# Requires `mangum` in requirements.txt
handler = None
try:
    from mangum import Mangum  # only used in Lambda
    handler = Mangum(app)
except ImportError:
    # Mangum not installed in local dev; ignore so local dev works with uvicorn
    handler = None


if __name__ == "__main__":
    # local development entrypoint (uvicorn)
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
