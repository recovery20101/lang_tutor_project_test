FROM node:22-alpine

WORKDIR /app

RUN apk add --no-cache netcat-openbsd

# Copy only dependency files first for Docker layer caching
COPY package*.json ./

# Copy frontend startup script and make it executable
COPY start-frontend.sh /usr/local/bin/start-frontend.sh
RUN chmod +x /usr/local/bin/start-frontend.sh

# The rest of the application code will be mounted via volume in docker-compose.yml

EXPOSE 3000

CMD ["start-frontend.sh"]