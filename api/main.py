# main.py

from fastapi import FastAPI

import sys
 
app = FastAPI(title="Multi-Cloud API")
 
 
@app.get("/")

async def root():

    """Root endpoint returning a simple JSON response"""

    return {"hi": "Hello from Multi-Cloud API!"}
 
 
@app.get("/health")

async def health():

    """Health check endpoint"""

    return {"status": "healthy"}
 
 
# ----------------------------

# Lambda handler using Mangum

# ----------------------------

try:

    from mangum import Mangum

    handler = Mangum(app)  # this is the AWS Lambda handler

except ImportError:

    # Mangum not installed locally, define a dummy handler to avoid errors

    handler = None
 
 
# ----------------------------

# Local development with uvicorn

# ----------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)

 
