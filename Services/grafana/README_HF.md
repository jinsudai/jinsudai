---
title: MLOps Energy Dashboard
emoji: 📊
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
license: mit
---

# Dashboard Grafana - MLOps Energy Prediction

Ce Space HuggingFace déploie un dashboard Grafana configuré pour le monitoring du projet MLOps de prédiction énergétique.

## 🚀 Fonctionnalités

- **Dashboard pré-configuré** avec les métriques clés du projet
- **Data sources automatiques** pour MLflow et EvidentlyAI
- **Monitoring en temps réel** des performances des modèles
- **Alertes visuelles** basées sur les seuils définis
- **Rafraîchissement automatique** toutes les 30 secondes

## 📊 Métriques surveillées

- **R² Score** : Performance des modèles (Consommation & Solaire)
- **MAE & RMSE** : Erreurs de prédiction
- **MAPE** : Mean Absolute Percentage Error
- **Temps d'inférence** : SLA < 100ms
- **Data Drift** : Détection de drift via EvidentlyAI
- **Volume d'activité** : Entraînements et prédictions

## 🔧 Configuration

### Variables d'environnement

Configurez les variables d'environnement dans les Settings du Space :

- `MLFLOW_URL` : URL du serveur MLflow (défaut: `http://localhost:5000`)
- `EVIDENTLY_URL` : URL du serveur EvidentlyAI (défaut: `http://localhost:8501`)
- `GF_SECURITY_ADMIN_USER` : Utilisateur admin Grafana (défaut: `admin`)
- `GF_SECURITY_ADMIN_PASSWORD` : Mot de passe admin Grafana (défaut: `admin`)

### Exemple de configuration

Si vos services MLflow et EvidentlyAI sont déployés sur HuggingFace :

```
MLFLOW_URL=https://votre-mlflow-space.hf.space
EVIDENTLY_URL=https://votre-evidently-space.hf.space
```

## 📦 Déploiement local

Pour tester localement avant le déploiement :

```bash
# Construire l'image Docker
docker build -t grafana-mlops-dashboard .

# Lancer le container
docker run -d \
  -p 7860:7860 \
  -e MLFLOW_URL=http://localhost:5000 \
  -e EVIDENTLY_URL=http://localhost:8501 \
  grafana-mlops-dashboard
```

Accéder au dashboard : `http://localhost:7860`

## 🌐 Déploiement sur HuggingFace Spaces

### Option 1 : Via l'interface web

1. Créer un nouveau Space sur HuggingFace
2. Choisir le SDK **Docker**
3.Uploader les fichiers :
   - `Dockerfile`
   - `datasources.yml`
   - `dashboard-provisioning.yml`
   - `dashboard.json`
   - `README.md` (ce fichier)
4. Configurer les variables d'environnement dans les Settings
5. Cliquer sur **Deploy**

### Option 2 : Via Git

```bash
# Cloner le repository
git clone https://huggingface.co/spaces/votre-username/votre-space-name

# Copier les fichiers
cp Services/grafana/* votre-space-name/

# Commit et push
cd votre-space-name
git add .
git commit -m "Add Grafana dashboard for MLOps monitoring"
git push
```

### Option 3 : Via le workflow GitHub existant

Le projet inclut déjà un workflow pour créer des Spaces HuggingFace. Utilisez le workflow `.github/workflows/hf_create_spaces.yaml` pour automatiser le déploiement.

## 🔐 Sécurité

Par défaut, le dashboard utilise les identifiants suivants :
- **Utilisateur** : `admin`
- **Mot de passe** : `admin`

**⚠️ Important** : Changez ces identifiants en production en configurant les variables d'environnement :
- `GF_SECURITY_ADMIN_USER`
- `GF_SECURITY_ADMIN_PASSWORD`

## 📝 Personnalisation

### Modifier le dashboard

1. Télécharger le fichier `dashboard.json`
2. Le modifier localement avec l'éditeur Grafana
3. Remplacer le fichier dans le Space
4. Redéployer

### Ajouter des data sources

1. Modifier `datasources.yml`
2. Ajouter la configuration de la nouvelle data source
3. Redéployer le Space

### Modifier les seuils d'alerte

Les seuils sont configurés dans `dashboard.json`. Modifiez les valeurs `thresholds` dans chaque panel pour ajuster les alertes.

## 🔍 Dépannage

### Problème : Data sources non connectées

**Solution** :
1. Vérifiez que les variables d'environnement sont correctement configurées
2. Vérifiez que les services MLflow et EvidentlyAI sont accessibles
3. Testez la connexion depuis le Space : `curl $MLFLOW_URL`

### Problème : Dashboard vide

**Solution** :
1. Vérifiez que le fichier `dashboard.json` est présent
2. Vérifiez les logs du Space pour les erreurs de provisioning
3. Assurez-vous que `dashboard-provisioning.yml` est correctement configuré

### Problème : Accès refusé

**Solution** :
1. Vérifiez les identifiants admin dans les Settings
2. Redémarrez le Space après avoir modifié les identifiants

## 📚 Documentation additionnelle

- [Documentation Grafana](https://grafana.com/docs/)
- [Documentation HuggingFace Spaces](https://huggingface.co/docs/hub/spaces)
- [Spécifications du projet](../../SPECIFICATIONS.md)
- [README principal du dashboard](./README.md)

## 🤝 Contribution

Pour contribuer à l'amélioration du dashboard :
1. Fork le projet
2. Modifiez les fichiers de configuration
3. Soumettez une pull request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.

---

**Développé pour le projet MLOps Energy Prediction - Jinsudai**
