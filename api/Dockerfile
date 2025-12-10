# =====================================

# Lambda image (AWS Lambda Runtime)

# =====================================

FROM public.ecr.aws/lambda/python:3.11 AS lambda
 
# Set working directory to Lambda root

WORKDIR /var/task
 
# Copy requirements and install into Lambda root

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt -t .
 
# Copy application source code

COPY main.py .
 
# Lambda handler

# 'handler' is the Mangum handler defined in main.py

CMD ["main.handler"]

 
