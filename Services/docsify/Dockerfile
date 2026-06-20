# Utilise une image Node.js légère
FROM node:18-alpine

# Installe Docsify et le plugin Mermaid
RUN npm install -g docsify-cli docsify-mermaid

# Crée le répertoire de travail
WORKDIR /docs

# Copie les fichiers de documentation
COPY . .

# Lance Docsify en mode serveur sur le port 7860 (port par défaut pour Hugging Face Spaces)
CMD ["docsify", "serve", "docs", "--port", "7860", "--open"]
