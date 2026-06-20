"""
Airflow DAG pour lancer un GitHub Action et attendre sa fin.

Ce DAG:
- Déclenche un workflow GitHub Action via l'API GitHub
- Attend que le workflow se termine
- Marque la tâche comme réussie si le workflow GitHub réussit
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.python import PythonSensor
import requests
import time
import os

# Configuration GitHub
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'owner/repo')
GITHUB_WORKFLOW = os.environ.get('GITHUB_WORKFLOW', 'workflow.yml')
GITHUB_BRANCH = os.environ.get('GITHUB_BRANCH', 'main')

def trigger_github_action(**context):
    """
    Déclenche un workflow GitHub Action via l'API GitHub.
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/dispatches"
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }
    
    payload = {
        'ref': GITHUB_BRANCH,
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 204:
        print(f"✅ Workflow {GITHUB_WORKFLOW} déclenché avec succès sur {GITHUB_BRANCH}")
        return {"status": "success", "run_id": None}
    else:
        print(f"❌ Erreur lors du déclenchement: {response.status_code} - {response.text}")
        raise Exception(f"Failed to trigger GitHub Action: {response.status_code}")

def check_github_action_status(**context):
    """
    Vérifie le statut du workflow GitHub Action.
    Retourne True si le workflow est terminé (succès ou échec).
    """
    # Récupérer le run le plus récent du workflow
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{GITHUB_WORKFLOW}/runs"
    
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
            
            print(f"📊 Statut du workflow: {status}, Conclusion: {conclusion}")
            
            # Le workflow est terminé si le status est 'completed'
            if status == 'completed':
                if conclusion == 'success':
                    print(f"✅ Workflow terminé avec succès")
                    return True
                else:
                    print(f"❌ Workflow terminé avec échec: {conclusion}")
                    raise Exception(f"GitHub Action failed: {conclusion}")
            else:
                print(f"⏳ Workflow en cours: {status}")
                return False
        else:
            print("⚠️ Aucun run trouvé")
            return False
    else:
        print(f"❌ Erreur lors de la vérification: {response.status_code}")
        raise Exception(f"Failed to check GitHub Action status: {response.status_code}")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'github_action_trigger',
    default_args=default_args,
    description='Déclenche un GitHub Action et attend sa fin',
    schedule=None,
    catchup=False,
    tags=['github', 'action', 'trigger'],
) as dag:
    
    trigger_task = PythonOperator(
        task_id='trigger_github_action',
        python_callable=trigger_github_action,
    )
    
    wait_task = PythonSensor(
        task_id='wait_for_github_action',
        python_callable=check_github_action_status,
        poke_interval=30,  # Vérifier toutes les 30 secondes
        timeout=3600,  # Timeout après 1 heure
        mode='poke',
    )
    
    # Dépendance: d'abord déclencher, puis attendre
    trigger_task >> wait_task
