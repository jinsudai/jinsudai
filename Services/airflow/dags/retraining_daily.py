"""
Airflow DAG pour le réentraînement quotidien conditionnel.

Logique:
- Exécution quotidienne
- Si drift détecté OU dernier réentraînement > 3 jours
- Réentraîner le modèle

Usage:
    Ce DAG est automatiquement schedulé par Airflow
    Peut aussi être déclenché manuellement via l'UI Airflow
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.slack.operators.slack import SlackAPIPostOperator

# Arguments par défaut du DAG
default_args = {
    'owner': 'jinsudai',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Création du DAG
dag = DAG(
    'retraining_daily',
    default_args=default_args,
    description='Réentraînement quotidien conditionnel (drift OU >3 jours)',
    schedule_interval='0 2 * * *',  # Exécution tous les jours à 2h du matin
    catchup=False,
    tags=['retraining', 'ml', 'consumption'],
)

# Tâche de réentraînement consommation
retrain_consumption = BashOperator(
    task_id='retrain_consumption_model',
    bash_command='cd /opt/jinsudai && python scripts/run_retraining.py --config consumption --max-days 3',
    dag=dag,
)

# Tâche de réentraînement solar production (optionnel)
retrain_solar = BashOperator(
    task_id='retrain_solar_model',
    bash_command='cd /opt/jinsudai && python scripts/run_retraining.py --config solar_production --max-days 3',
    dag=dag,
)

# Notification Slack en cas de succès (optionnel)
notify_success = SlackAPIPostOperator(
    task_id='notify_success',
    slack_conn_id='slack_default',
    channel='#ml-ops',
    text='✅ Réentraînement quotidien terminé avec succès',
    dag=dag,
)

# Notification Slack en cas d'échec (optionnel)
notify_failure = SlackAPIPostOperator(
    task_id='notify_failure',
    slack_conn_id='slack_default',
    channel='#ml-ops',
    text='❌ Échec du réentraînement quotidien',
    dag=dag,
    trigger_rule='one_failed',
)

# Dépendances
retrain_consumption >> [notify_success, notify_failure]
retrain_solar >> [notify_success, notify_failure]
