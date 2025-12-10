# main.py

from fastapi import FastAPI
 
app = FastAPI(title="Multi-Cloud API")
 
# ----------------------------

# Endpoints

# ----------------------------

@app.get("/")

async def root():

    """Root endpoint returning a simple JSON response"""

    return {"message": "Hello from Multi-Cloud API!"}
 
@app.get("/health")

async def health():

    """Health check endpoint"""

    return {"status": "healthy"}
 
# ----------------------------

# Lambda handler (Mangum)

# ----------------------------

try:

    from mangum import Mangum

    handler = Mangum(app)  # AWS Lambda entrypoint

except ImportError:

    # Mangum not installed in local dev; fallback to None

    handler = None
 
# ----------------------------

# Local development

# ----------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)

 
