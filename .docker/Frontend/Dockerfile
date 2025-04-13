ARG NODE_VERSION
FROM node:${NODE_VERSION}-alpine

WORKDIR /app/frontend

COPY ../../frontend/package*.json ./
RUN npm install

EXPOSE 3000