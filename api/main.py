# main.py
from fastapi import FastAPI
from fastapi.responses import JSONResponse
try:
    # Mangum is optional at runtime — only required for Lambda deployments
    from mangum import Mangum
    _HAS_MANGUM = True
except Exception:
    _HAS_MANGUM = False

app = FastAPI(title="Multi-Cloud API")


@app.get("/")
async def root():
    """Root endpoint returning a simple JSON response"""
    return {"hi": "Hello from Multi-Cloud API!"}


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# Lambda handler (Mangum) — only used when running in Lambda
if _HAS_MANGUM:
    handler = Mangum(app)   # Lambda entrypoint: module.handler
