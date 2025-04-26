ARG PY_VERSION=3.13
FROM python:${PY_VERSION}-slim

WORKDIR /app/backend

COPY ../../backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
