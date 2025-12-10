# api/Dockerfile
# Multi-stage: dev (uvicorn) and lambda (AWS Lambda base image).
# Build dev: docker build --target dev -t my-api:dev .
# Build lambda: docker build --target lambda -t my-api:lambda .

FROM python:3.11-slim AS base
WORKDIR /app
# Copy requirements early for better cache
COPY requirements.txt .
# Install deps into a local folder so we can copy them into lambda stage
# Using --no-deps avoids double-install but keep it full for simplicity
RUN python -m pip install --no-cache-dir -r requirements.txt -t /app/_deps

# Copy application source
COPY . .

# DEV image (long-running server)
FROM python:3.11-slim AS dev
WORKDIR /app
# copy installed deps and app files
COPY --from=base /app/_deps /usr/local/lib/python3.11/site-packages/
COPY --from=base /app /app
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

# LAMBDA image (must include dependencies under /var/task)
FROM public.ecr.aws/lambda/python:3.11 AS lambda
WORKDIR /var/task
# Copy app files
COPY --from=base /app /var/task
# Copy the vendored deps into the lambda root so they are importable
COPY --from=base /app/_deps /var/task/
# Tell Lambda runtime which handler to call
CMD ["main.handler"]
