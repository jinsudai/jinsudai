FROM node:22-alpine

RUN apk add --no-cache git

WORKDIR /app

COPY package.json ./
COPY slides.md /app
RUN npm install

COPY . .

RUN npm run build

RUN npm install -g serve

EXPOSE 7860

CMD ["sh", "-c", "serve dist -l 7860"]