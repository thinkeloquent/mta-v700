FROM node:22-slim

WORKDIR /app

# Copy package files
COPY packages_mjs/db-connection-elasticsearch /packages/db-connection-elasticsearch
COPY examples/fastify-example/package.json examples/fastify-example/tsconfig.json ./
COPY examples/fastify-example/src ./src

# Update package.json for Docker context
RUN sed -i 's|file:../../packages_mjs/db-connection-elasticsearch|file:/packages/db-connection-elasticsearch|' package.json

# Build the local package first
WORKDIR /packages/db-connection-elasticsearch
RUN npm install && npm run build

# Install app dependencies
WORKDIR /app
RUN npm install

EXPOSE 3000

CMD ["node", "src/server.js"]
