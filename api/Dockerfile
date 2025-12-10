# =====================================

# Base stage - install dependencies

# =====================================

FROM python:3.11-slim AS base

WORKDIR /app
 
# Install dependencies into a vendor directory

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt -t /app/deps
 
# Copy application source

COPY . .
 
 
# =====================================

# Development image (uvicorn)

# =====================================

FROM python:3.11-slim AS dev

WORKDIR /app
 
# Copy dependencies and app code

COPY --from=base /app/deps /usr/local/lib/python3.11/site-packages/

COPY --from=base /app /app
 
EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
 
 
# =====================================

# Lambda image (AWS Lambda Runtime)

# =====================================

FROM public.ecr.aws/lambda/python:3.11 AS lambda
 
# Lambda WORKDIR must be /var/task

WORKDIR /var/task
 
# Copy dependencies FIRST into the Lambda root directory

COPY --from=base /app/deps/ /var/task/
 
# Copy app code DIRECTLY into /var/task (NOT inside /app)

# This ensures main.py is at /var/task/main.py as Lambda requires

COPY --from=base /app/*.py /var/task/

COPY --from=base /app/* /var/task/
 
# Lambda entrypoint

CMD ["main.handler"]

 
