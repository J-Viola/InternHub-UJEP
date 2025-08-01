ARG PG_VERSION
FROM postgres:${PG_VERSION}

WORKDIR /app/database

COPY ./.docker/Database/init.sql .
COPY ./.docker/Database/startup.sh .

# Opravíme line endings a nastavíme execute permissions
RUN sed -i 's/\r$//' startup.sh && chmod +x startup.sh

ENTRYPOINT ["bash", "/app/database/startup.sh"]