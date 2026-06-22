"""
Point d'entrée pour le serveur Evidently UI.

Ce script lance le serveur UI d'EvidentlyAI pour visualiser les rapports de monitoring.
"""

import os
from pathlib import Path
from evidently.ui.workspace import Workspace
from evidently.ui.dashboards import DashboardPanelPlot, DashboardPanelCounter, ReportFilter
from evidently.ui.base import Project
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
from evidently.metrics import DatasetDriftMetric
from evidently.descriptors import Descriptor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
WORKSPACE_PATH = os.getenv("EVIDENTLY_WORKSPACE_PATH", "/app/workspace")
HOST = os.getenv("EVIDENTLY_HOST", "0.0.0.0")
PORT = int(os.getenv("EVIDENTLY_PORT", "8000"))

def create_workspace():
    """Crée ou charge le workspace Evidently."""
    workspace_path = Path(WORKSPACE_PATH)
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    workspace = Workspace.create(workspace_path)
    logger.info(f"Workspace créé/chargé: {workspace_path}")
    
    return workspace

def create_project(workspace: Workspace, project_name: str = "energy_consumption"):
    """Crée un projet dans le workspace."""
    try:
        project = workspace.create_project(project_name)
        project.description = "Monitoring de la consommation d'énergie - Data Drift et Concept Drift"
        project.dashboard.add_panel(
            DashboardPanelCounter(
                title="Nombre de rapports",
                filter=ReportFilter(metadata_values={}, tag_values=[]),
                agg="count",
                metric_id="dataset_drift",
            )
        )
        project.dashboard.add_panel(
            DashboardPanelPlot(
                title="Drift Score dans le temps",
                filter=ReportFilter(metadata_values={}, tag_values=[]),
                metric_id="dataset_drift",
                metric_name="drift_score",
                plot_type="line",
            )
        )
        project.save()
        logger.info(f"Projet créé: {project_name}")
        return project
    except Exception as e:
        logger.warning(f"Le projet existe déjà ou erreur lors de la création: {e}")
        # Essayer de charger le projet existant
        return workspace.get_project(project_name)

def main():
    """Point d'entrée principal."""
    logger.info("Démarrage du serveur Evidently UI...")
    
    # Créer le workspace
    workspace = create_workspace()
    
    # Créer le projet par défaut
    project = create_project(workspace, "energy_consumption")
    
    # Lancer le serveur UI
    logger.info(f"Serveur UI accessible sur http://{HOST}:{PORT}")
    logger.info(f"Workspace path: {WORKSPACE_PATH}")
    
    from evidently.ui import start_server
    
    start_server(
        workspace=workspace,
        host=HOST,
        port=PORT,
        workspace_base_path=WORKSPACE_PATH
    )

if __name__ == "__main__":
    main()
