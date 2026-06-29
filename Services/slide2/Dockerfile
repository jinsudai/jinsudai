FROM node:22-alpine

# Install dependencies for Slidev
RUN apk add --no-cache git

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy slides and other files
COPY . .

# Build the presentation
RUN npm run build

# Install a simple HTTP server to serve the built files
RUN npm install -g serve

# Expose port 7860 (Hugging Face Spaces default)
EXPOSE 7860

# Serve the built presentation
CMD ["serve", "-s", "dist", "-l", "7860"]
