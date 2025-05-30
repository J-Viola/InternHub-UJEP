ARG PY_VERSION
FROM python:${PY_VERSION}

WORKDIR /app/backend

COPY ../../backend/requirements.txt .
RUN pip install debugpy
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
EXPOSE 5678