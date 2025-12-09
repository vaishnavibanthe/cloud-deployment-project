# Dockerfile for Lambda container image (uses AWS Lambda base image)
FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
WORKDIR /var/task
# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# For local dev you can still run: uvicorn main:app --reload --port 8080
# But in Lambda we MUST set the handler as the container CMD:
# The handler value is "<file>.<callable>" where Mangum's handler is `handler` set in main.py
CMD ["main.handler"]
