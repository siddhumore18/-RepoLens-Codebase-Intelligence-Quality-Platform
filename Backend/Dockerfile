FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3001

ENV PORT=3001
ENV AI_SERVICE_URL=http://ai-model:5000

CMD ["node", "server.js"]
