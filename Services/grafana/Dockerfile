# Dockerfile pour déploiement Grafana sur HuggingFace Spaces
# Ce Dockerfile installe Grafana avec les configurations pré-chargées

FROM grafana/grafana:10.2.0

# Installer les dépendances nécessaires
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer les répertoires de provisioning
RUN mkdir -p /etc/grafana/provisioning/datasources \
    && mkdir -p /etc/grafana/provisioning/dashboards \
    && mkdir -p /var/lib/grafana/dashboards

# Copier les configurations de provisioning
COPY datasources.yml /etc/grafana/provisioning/datasources/datasources.yml
COPY dashboard-provisioning.yml /etc/grafana/provisioning/dashboards/dashboard-provisioning.yml

# Copier le dashboard
COPY dashboard.json /var/lib/grafana/dashboards/dashboard.json

# Définir les permissions
RUN chown -R grafana:grafana /etc/grafana/provisioning \
    && chown -R grafana:grafana /var/lib/grafana/dashboards

# Configuration de l'environnement Grafana
ENV GF_SECURITY_ADMIN_USER=admin
ENV GF_SECURITY_ADMIN_PASSWORD=admin
ENV GF_USERS_ALLOW_SIGN_UP=false
ENV GF_SERVER_HTTP_PORT=7860
ENV GF_SERVER_ROOT_URL=%(protocol)s://%(domain)s:%(http_port)s/
ENV GF_INSTALL_PLUGINS=

# Exposer le port 7860 (requis par HuggingFace Spaces)
EXPOSE 7860

# Commande de démarrage
CMD ["grafana-server"]
