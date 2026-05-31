FROM node:20-alpine

WORKDIR /app

ARG API_INTERNAL_URL=http://api:8000
ENV NODE_ENV=development
ENV API_INTERNAL_URL=${API_INTERNAL_URL}

COPY package.json package-lock.json* ./
RUN npm ci --frozen-lockfile 2>/dev/null || npm install

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
