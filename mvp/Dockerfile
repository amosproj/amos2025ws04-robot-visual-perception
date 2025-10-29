FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY public ./public

EXPOSE 5173

CMD ["npm", "start"]
