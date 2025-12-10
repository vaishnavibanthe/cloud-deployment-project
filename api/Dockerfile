# =====================================

# Lambda image

# =====================================

FROM public.ecr.aws/lambda/python:3.11
 
WORKDIR /var/task
 
# Copy requirements and install into Lambda root

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt -t .
 
# Copy app source code

COPY main.py .
 
# Lambda entrypoint

CMD ["main.handler"]

 
