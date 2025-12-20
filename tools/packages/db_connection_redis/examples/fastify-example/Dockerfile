FROM node:22-slim

WORKDIR /app

# Copy package files
COPY packages_mjs/db_connection_redis /packages/db_connection_redis
COPY examples/fastify-example/package.json ./
COPY examples/fastify-example/src ./src

# Update package.json for Docker context
RUN sed -i 's|file:../../packages_mjs/db_connection_redis|file:/packages/db_connection_redis|' package.json

# Install local package dependencies first
WORKDIR /packages/db_connection_redis
RUN npm install

# Install app dependencies
WORKDIR /app
RUN npm install

EXPOSE 3000

CMD ["node", "src/server.mjs"]
