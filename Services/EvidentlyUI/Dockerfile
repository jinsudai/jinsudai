# Utilise une image Node.js légère
FROM node:18-alpine

# Installe Marp CLI
RUN npm install -g @marp-team/marp-cli

# Crée le répertoire de travail
WORKDIR /app

# Copie les fichiers de présentation
COPY . .

# Expose le port 7860 (port par défaut pour Hugging Face Spaces)
EXPOSE 7860

# Lance un serveur simple pour servir la présentation HTML
# Marp génère un fichier HTML statique, nous servons celui-ci
RUN npm install -g http-server

# Commande pour générer et servir la présentation
CMD ["sh", "-c", "marp slides.md --html --output /tmp/presentation.html && http-server /tmp -p 7860"]
