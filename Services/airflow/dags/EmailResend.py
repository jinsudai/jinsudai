from airflow.sdk.bases.hook import BaseHook
import requests
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime
import os

def send_email():
    #api_key = os.environ["RESEND_API_KEY"]
    conn = BaseHook.get_connection("resend_api")

    api_key = conn.password
    #base_url = "https://api.resend.com/emails"
    base_url = conn.host

    response = requests.post(
        f"{base_url}/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "from": "jenedai@sustcoop.fr",
            "to": "jenedai@free.fr",
            "subject": "Email depuis Airflow",
            "html": "<p>Hello depuis DAG Airflow 🚀</p>"
        }
    )

    if response.status_code != 200:
        raise Exception(response.text)

with DAG(
    dag_id="resend_email_dag",
    start_date=datetime(2024, 1, 1),
    schedule=None,
    catchup=False
) as dag:

    task = PythonOperator(
        task_id="send_email_api",
        python_callable=send_email
    )