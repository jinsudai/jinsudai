"""
DAG maître pour orchestrer tous les pipelines MLOps avec dépendances explicites.

Ce DAG orchestre l'exécution séquentielle des pipelines en utilisant TriggerDagRunOperator:
1. Ingestion des actuals (0h30)
2. Préparation des données (1h)
3. Monitoring et drift detection (1h30)
4. Training conditionnel (2h) - si drift ou dernier training > 1 jour
5. Inférence (3h)

NOTE: Les DAGs individuels doivent avoir leurs schedules désactivés pour éviter les conflits.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.operators.python import BranchPythonOperator
from airflow.sensors.datetime import DateTimeSensor
import sys
import os

# Ajouter le dossier utils au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'utils'))
from github_action_helper import should_trigger_training

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
    'master_pipeline',
    default_args=default_args,
    description='DAG maître orchestrant tous les pipelines MLOps',
    schedule='30 0 * * *',  # Tous les jours à 0h30
    catchup=False,
    tags=['master', 'orchestration', 'mlops'],
) as dag:
    
    # Point de départ
    start = EmptyOperator(task_id='start')
    
    # 1. Déclencher l'ingestion
    trigger_ingestion = TriggerDagRunOperator(
        task_id='trigger_ingestion',
        trigger_dag_id='ingestion_pipeline',
        wait_for_completion=True,
        poke_interval=30,
        allowed_states=['success'],
        failed_states=['failed'],
    )
    
    # 2. Déclencher la préparation
    trigger_preparation = TriggerDagRunOperator(
        task_id='trigger_preparation',
        trigger_dag_id='preparation_pipeline',
        wait_for_completion=True,
        poke_interval=30,
        allowed_states=['success'],
        failed_states=['failed'],
    )
    
    # 3. Déclencher le monitoring
    trigger_monitoring = TriggerDagRunOperator(
        task_id='trigger_monitoring',
        trigger_dag_id='monitoring_pipeline',
        wait_for_completion=True,
        poke_interval=30,
        allowed_states=['success'],
        failed_states=['failed'],
    )
    
    # 4. Attendre jusqu'à 3h du matin pour l'inférence
    wait_until_3h = DateTimeSensor(
        task_id='wait_until_3h',
        target_time=lambda dt: dt.replace(hour=3, minute=0, second=0, microsecond=0) + (timedelta(days=1) if dt.hour >= 3 else timedelta(0)),
        mode='reschedule',  # Libère le worker pendant l'attente
    )
    
    # 5. Déclencher l'inférence (en parallèle, à 3h du matin)
    trigger_inference = TriggerDagRunOperator(
        task_id='trigger_inference',
        trigger_dag_id='inference_pipeline',
        wait_for_completion=True,
        poke_interval=30,
        allowed_states=['success'],
        failed_states=['failed'],
    )
    
    # 6. Vérifier si le training est nécessaire
    check_training_needed = BranchPythonOperator(
        task_id='check_training_needed',
        python_callable=should_trigger_training,
    )
    
    # 7. Déclencher le training (si nécessaire)
    trigger_training = TriggerDagRunOperator(
        task_id='trigger_training',
        trigger_dag_id='training_pipeline',
        wait_for_completion=True,
        poke_interval=30,
        allowed_states=['success'],
        failed_states=['failed'],
    )
    
    # Point de fin pour le branch skip
    skip_training = EmptyOperator(task_id='skip_training')
    
    # Point de fin
    end = EmptyOperator(task_id='end')
    
    # Dépendances
    start >> trigger_ingestion
    trigger_ingestion >> trigger_preparation
    trigger_preparation >> trigger_monitoring
    
    # Training conditionnel après monitoring
    trigger_monitoring >> check_training_needed
    
    # Branch conditionnelle pour training
    check_training_needed >> [trigger_training, skip_training]
    
    # Fin du pipeline training
    [trigger_training, skip_training] >> end
    
    # Inférence en parallèle: start → wait until 3h → inference → end
    start >> wait_until_3h
    wait_until_3h >> trigger_inference
    trigger_inference >> end
