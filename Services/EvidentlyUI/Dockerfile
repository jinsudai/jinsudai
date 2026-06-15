FROM python:3.11-slim

WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de configuration
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Créer le workspace Evidently
RUN mkdir -p /app/workspace

# Copier le point d'entrée
COPY main.py .

# Exposer le port
EXPOSE 8000

# Commande de démarrage
CMD ["python", "main.py"]
