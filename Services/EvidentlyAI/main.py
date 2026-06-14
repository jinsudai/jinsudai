"""
Dashboard Evidently AI pour le monitoring des modèles ML.
Ce dashboard affiche les rapports de drift detection et les métriques de performance.
"""

import streamlit as st
import pandas as pd
import os
from pathlib import Path
import yaml
from datetime import datetime, timedelta
import mlflow

# Configuration de la page
st.set_page_config(
    page_title="Evidently AI Dashboard",
    page_icon="📊",
    layout="wide"
)

# Titre
st.title("📊 Evidently AI Dashboard")
st.markdown("---")

# Configuration
@st.cache_resource
def load_config():
    """Charge la configuration depuis config.yaml"""
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}

config = load_config()

# Sidebar pour la configuration
st.sidebar.header("Configuration")

# Configuration MLflow
mlflow_tracking_uri = st.sidebar.text_input(
    "MLflow Tracking URI",
    value=config.get("mlflow", {}).get("tracking_uri", "http://localhost:5000"),
    help="URI du serveur MLflow"
)

experiment_name = st.sidebar.text_input(
    "Experiment Name",
    value=config.get("mlflow", {}).get("default_experiment_name", "energy_consumption"),
    help="Nom de l'expérience MLflow"
)

# Configuration de la période
st.sidebar.header("Période d'analyse")
days_back = st.sidebar.slider(
    "Jours à analyser",
    min_value=1,
    max_value=30,
    value=7,
    help="Nombre de jours à analyser pour les métriques"
)

# Connexion MLflow
try:
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    st.sidebar.success("✅ Connecté à MLflow")
except Exception as e:
    st.sidebar.error(f"❌ Erreur de connexion MLflow: {e}")

# Fonction pour charger les rapports Evidently
def load_evidently_reports():
    """Charge les rapports Evidently depuis MLflow"""
    reports = []
    try:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment:
            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"]
            )
            
            for run in runs:
                run_id = run.info.run_id
                artifacts = mlflow.artifacts.list_artifacts(run_id)
                
                for artifact in artifacts:
                    if artifact.path.endswith(".html") and "drift" in artifact.path.lower():
                        reports.append({
                            "run_id": run_id,
                            "artifact_path": artifact.path,
                            "start_time": run.info.start_time,
                            "metrics": run.data.metrics
                        })
    except Exception as e:
        st.error(f"Erreur lors du chargement des rapports: {e}")
    
    return reports

# Fonction pour afficher les métriques de drift
def display_drift_metrics(metrics):
    """Affiche les métriques de drift"""
    if not metrics:
        st.info("Aucune métrique disponible")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        dataset_drift = metrics.get("dataset_drift", 0)
        st.metric(
            "Data Drift",
            "Détecté" if dataset_drift else "Non détecté",
            delta_color="inverse" if dataset_drift else "normal"
        )
    
    with col2:
        drifted_features = metrics.get("drifted_features", 0)
        st.metric("Features en drift", drifted_features)
    
    with col3:
        total_features = metrics.get("total_features", 0)
        st.metric("Total features", total_features)

# Main content
st.header("Rapports de Drift Detection")

# Charger les rapports
reports = load_evidently_reports()

if reports:
    st.info(f"📊 {len(reports)} rapport(s) trouvé(s)")
    
    # Sélectionner un rapport
    report_options = [
        f"Run {r['run_id'][:8]} - {datetime.fromtimestamp(r['start_time']/1000).strftime('%Y-%m-%d %H:%M')}"
        for r in reports
    ]
    
    selected_report = st.selectbox("Sélectionner un rapport", report_options)
    
    if selected_report:
        idx = report_options.index(selected_report)
        report = reports[idx]
        
        # Afficher les métriques
        st.subheader("Métriques de Drift")
        display_drift_metrics(report["metrics"])
        
        # Afficher le rapport HTML
        st.subheader("Rapport Détaillé")
        
        try:
            # Télécharger et afficher le rapport HTML
            local_path = mlflow.artifacts.download_artifacts(
                report["artifact_path"],
                dst_path=f"/tmp/{report['run_id']}"
            )
            
            with open(local_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            st.components.v1.html(html_content, height=800, scrolling=True)
        except Exception as e:
            st.error(f"Erreur lors de l'affichage du rapport: {e}")
else:
    st.warning("⚠️ Aucun rapport Evidently trouvé. Exécutez d'abord la détection de drift dans le pipeline.")

# Section pour générer un nouveau rapport
st.markdown("---")
st.header("Générer un nouveau rapport")

st.info("💡 Les rapports sont générés automatiquement lors de l'exécution du pipeline de prédiction avec la détection de drift activée.")

# Informations sur le système
st.markdown("---")
st.subheader("Informations système")
col1, col2 = st.columns(2)

with col1:
    st.metric("Environnement", os.getenv("ENV", "dev"))

with col2:
    st.metric("Date du jour", datetime.now().strftime("%Y-%m-%d"))
