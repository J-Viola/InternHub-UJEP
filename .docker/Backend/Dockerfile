ARG PY_VERSION
FROM python:${PY_VERSION}

WORKDIR /app/backend

COPY ../../backend/requirements.txt .
RUN pip install debugpy
RUN pip install --no-cache-dir -r requirements.txt

COPY .docker/Backend/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
EXPOSE 5678

ENTRYPOINT ["/entrypoint.sh"]