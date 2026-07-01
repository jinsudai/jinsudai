"""
Module utilitaire mutualisé pour déclencher des GitHub Actions depuis Airflow.

Ce module fournit des fonctions réutilisables pour:
- Déclencher un workflow GitHub Action
- Attendre la fin de l'exécution
- Gérer les erreurs et les timeouts
- Vérifier si un training est nécessaire (drift ou temps écoulé)
"""
import requests
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Configuration GitHub (variables d'environnement)
GITHUB_TOKEN = os.environ.get('GH_TOKEN')
GITHUB_REPO = os.environ.get('GH_REPO', 'owner/repo')
GITHUB_BRANCH = os.environ.get('GH_BRANCH', 'main')


def trigger_github_action(github_workflow: str, branch: Optional[str] = None) -> Dict[str, Any]:
    """
    Déclenche un workflow GitHub Action via l'API GitHub.
    
    Args:
        github_workflow: Nom du fichier workflow (ex: '1_actuals_ingestion_pipeline.yml')
        branch: Branche à utiliser (défaut: GITHUB_BRANCH)
    
    Returns:
        Dict avec le statut et le workflow déclenché
    
    Raises:
        Exception: Si le déclenchement échoue
    """
    target_branch = branch or GITHUB_BRANCH
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{github_workflow}/dispatches"
    
    print(f"🔗 URL de l'API GitHub: {url}")
    print(f"📦 Repo: {GITHUB_REPO}")
    print(f"📄 Workflow: {github_workflow}")
    print(f"🌿 Branch: {target_branch}")
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }
    
    payload = {
        'ref': target_branch,
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 204:
        print(f"✅ Workflow {github_workflow} déclenché avec succès sur {target_branch}")
        return {"status": "success", "workflow": github_workflow, "branch": target_branch}
    else:
        print(f"❌ Erreur lors du déclenchement: {response.status_code} - {response.text}")
        raise Exception(f"Failed to trigger GitHub Action: {response.status_code}")


def check_github_action_status(github_workflow: str, branch: Optional[str] = None, check_drift: bool = False, **context) -> bool:
    """
    Vérifie le statut du workflow GitHub Action.
    
    Args:
        github_workflow: Nom du fichier workflow
        branch: Branche à vérifier (défaut: GITHUB_BRANCH)
        check_drift: Si True, vérifie si un drift a été détecté (pour monitoring)
        context: Context Airflow pour passer les XComs
    
    Returns:
        True si le workflow est terminé avec succès
    
    Raises:
        Exception: Si le workflow échoue ou si l'API retourne une erreur
    """
    target_branch = branch or GITHUB_BRANCH
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{github_workflow}/runs"
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        runs = response.json().get('workflow_runs', [])
        if runs:
            latest_run = runs[0]
            status = latest_run.get('status')
            conclusion = latest_run.get('conclusion')
            
            print(f"📊 Statut du workflow {github_workflow}: {status}, Conclusion: {conclusion}")
            
            # Le workflow est terminé si le status est 'completed'
            if status == 'completed':
                if conclusion == 'success':
                    print(f"✅ Workflow {github_workflow} terminé avec succès")
                    
                    # Si c'est le monitoring et qu'on doit vérifier le drift
                    if check_drift and context:
                        # Pour l'instant, on simule le drift detection
                        # TODO: Implémenter la vraie logique de drift detection
                        # en lisant les artefacts du workflow ou en appelant une API
                        drift_detected = False  # À remplacer par la vraie logique
                        task_instance = context['task_instance']
                        task_instance.xcom_push(key='drift_detected', value=drift_detected)
                        print(f"🔍 Drift détecté: {drift_detected}")
                    
                    return True
                else:
                    print(f"❌ Workflow {github_workflow} terminé avec échec: {conclusion}")
                    raise Exception(f"GitHub Action failed: {conclusion}")
            else:
                print(f"⏳ Workflow {github_workflow} en cours: {status}")
                return False
        else:
            print("⚠️ Aucun run trouvé")
            return False
    else:
        print(f"❌ Erreur lors de la vérification: {response.status_code}")
        raise Exception(f"Failed to check GitHub Action status: {response.status_code}")


def get_workflow_runs(github_workflow: str, limit: int = 5) -> list:
    """
    Récupère les derniers runs d'un workflow GitHub Action.
    
    Args:
        github_workflow: Nom du fichier workflow
        limit: Nombre maximum de runs à retourner
    
    Returns:
        Liste des runs
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{github_workflow}/runs"
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        runs = response.json().get('workflow_runs', [])
        return runs[:limit]
    else:
        raise Exception(f"Failed to get workflow runs: {response.status_code}")


def should_trigger_training(**context) -> str:
    """
    Détermine si le training doit être déclenché.
    
    Vérifie:
    1. Si le monitoring a détecté un data drift (via XCom)
    2. Si le dernier training date est > 1 jour
    
    Args:
        context: Context Airflow avec accès aux XComs
    
    Returns:
        'trigger_training' si le training doit être déclenché, 'skip_training' sinon
    """
    # Récupérer le drift status depuis le monitoring (via XCom)
    task_instance = context['task_instance']
    drift_detected = task_instance.xcom_pull(task_ids='wait_for_github_action', key='drift_detected')
    
    # Récupérer la date du dernier training
    try:
        training_runs = get_workflow_runs('3_training-pipeline.yml', limit=1)
        if training_runs:
            last_training_date = datetime.strptime(training_runs[0]['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            days_since_last_training = (datetime.now() - last_training_date).days
            training_needed = days_since_last_training > 1
        else:
            # Aucun training précédent, déclencher
            training_needed = True
            days_since_last_training = None
    except Exception as e:
        print(f"⚠️ Erreur lors de la récupération du dernier training: {e}")
        # En cas d'erreur, déclencher le training par sécurité
        training_needed = True
        days_since_last_training = None
    
    # Décision: training si drift OU dernier training > 1 jour
    should_train = drift_detected or training_needed
    
    print(f"📊 Décision training:")
    print(f"   - Drift détecté: {drift_detected}")
    print(f"   - Dernier training: {days_since_last_training} jours" if days_since_last_training else "   - Dernier training: inconnu")
    print(f"   - Training nécessaire: {training_needed}")
    print(f"   - Décision finale: {'TRAIN' if should_train else 'SKIP'}")
    
    return 'trigger_training' if should_train else 'skip_training'
