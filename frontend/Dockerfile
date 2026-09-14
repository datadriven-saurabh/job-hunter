FROM node:22-alpine
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
CMD ["npx", "next", "start", "--hostname", "0.0.0.0"]
