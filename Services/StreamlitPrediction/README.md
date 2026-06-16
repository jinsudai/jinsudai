# Streamlit Prediction Service

Service Streamlit pour demander les prédictions de consommation énergétique sur 48 heures (ou plusieurs jours selon les limites de l'API météo).

## Fonctionnalités

- **Prévisions météo**: Récupération automatique des prévisions météo via l'API Open-Meteo (jusqu'à 16 jours)
- **Prédictions ML**: Génération de prédictions de consommation utilisant le modèle MLflow en production
- **Interface interactive**: Interface web intuitive avec Streamlit
- **Visualisation**: Graphiques interactifs pour les prévisions météo et les prédictions de consommation
- **Export**: Export des prédictions en CSV ou Parquet
- **Configuration flexible**: Sélection de la localisation, nombre de jours, et échantillons par jour

## Configuration

### Variables d'environnement

Le service utilise les variables d'environnement suivantes (définies dans `.env` ou `config.yaml`):

- `MLFLOW_TRACKING_URI`: URI du serveur MLflow (défaut: `http://localhost:5000`)
- `MLFLOW_EXPERIMENT_NAME`: Nom de l'expérience MLflow (défaut: `consumption_experiment`)
- `MLFLOW_MODEL_NAME`: Nom du modèle dans MLflow
- `DATABASE_URI`: URI de connexion PostgreSQL (optionnel)

### Paramètres de l'interface

- **Latitude/Longitude**: Coordonnées géographiques pour les prévisions météo (défaut: Paris)
- **Nombre de jours**: Nombre de jours de prévision (1-16 jours selon API Open-Meteo)
- **Échantillons par jour**: Nombre d'échantillons par jour (24, 48, ou 96; défaut: 48 pour 30min)

## Installation

### Localement

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le service
streamlit run main.py
```

Le service sera accessible sur `http://localhost:8501`

### Avec Docker

```bash
# Construire l'image
docker build -t streamlit-prediction .

# Lancer le conteneur
docker run -p 8501:8501 \
  -e MLFLOW_TRACKING_URI=http://mlflow:5000 \
  -e DATABASE_URI=postgresql://user:pass@db:5432/predictions \
  streamlit-prediction
```

### Avec Docker Compose

Ajouter ce service à votre `docker-compose.yml`:

```yaml
services:
  streamlit-prediction:
    build: ./Services/StreamlitPrediction
    ports:
      - "8501:8501"
    environment:
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - DATABASE_URI=postgresql://user:pass@db:5432/predictions
    depends_on:
      - mlflow
      - db
```

## Utilisation

1. **Configurer la localisation**: Utilisez la barre latérale pour définir la latitude et longitude
2. **Sélectionner la période**: Choisissez le nombre de jours de prévision (1-16)
3. **Générer les prédictions**: Cliquez sur le bouton "Générer les prédictions de consommation"
4. **Visualiser les résultats**: 
   - Statistiques météo (température, humidité, précipitations)
   - Graphiques d'évolution météo
   - Statistiques des prédictions de consommation
   - Courbe des prédictions
   - Scores de confiance (si disponibles)
5. **Exporter les données**: Téléchargez les prédictions en CSV ou Parquet

## Architecture

Le service utilise les composants existants du projet:

- **WeatherAPI**: Récupération des prévisions météo depuis Open-Meteo
- **InferenceModel**: Chargement et utilisation du modèle MLflow
- **generate_inference_data**: Génération des données d'inférence avec météo et vacances
- **add_predictions_to_data**: Ajout des prédictions au DataFrame

## Dépendances

- `streamlit>=1.58.0,<2.0.0`: Framework d'interface web
- `plotly>=5.0.0`: Graphiques interactifs
- `pandas>=2.0.0`: Manipulation des données
- `numpy>=1.24.0`: Calculs numériques
- `requests>=2.28.0`: Requêtes HTTP pour l'API météo
- `pyarrow>=10.0.0`: Support Parquet
- `python-dotenv>=1.0.0`: Gestion des variables d'environnement

## Limitations

- L'API Open-Meteo permet des prévisions jusqu'à 16 jours maximum
- Le nombre d'échantillons par jour doit être un multiple de 24 (horaire)
- Le modèle ML doit être disponible dans MLflow avec l'alias "prod"

## Dépannage

### Erreur: "Failed to load model"

Vérifiez que:
- MLflow est accessible et en cours d'exécution
- Le modèle existe avec le bon nom et l'alias "prod"
- Les variables d'environnement MLFLOW sont correctement configurées

### Erreur: "Failed to fetch weather forecast"

Vérifiez que:
- Vous avez une connexion internet active
- L'API Open-Meteo est accessible
- Les coordonnées latitude/longitude sont valides

### Erreur: "Failed to generate predictions"

Vérifiez que:
- Les données météo ont été récupérées avec succès
- Le modèle est chargé correctement
- Les colonnes features correspondent à celles attendues par le modèle

## Développement

Pour tester localement avec le code source du projet:

```bash
# Depuis la racine du projet
cd Services/StreamlitPrediction

# Lancer avec le code source
PYTHONPATH=../../src:$PYTHONPATH streamlit run main.py
```

## Licence

Voir le fichier LICENSE à la racine du projet.
