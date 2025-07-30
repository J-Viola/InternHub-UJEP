ARG PG_VERSION
FROM postgres:${PG_VERSION}

WORKDIR /app/database

COPY ./.docker/Database/init.sql .
COPY ./.docker/Database/startup.sh .

RUN chmod +x startup.sh

ENTRYPOINT ["./startup.sh"]