# Use an official Airflow image as base
FROM apache/airflow:3.1.7

# Apply the Hugging Faces secrets
ARG AIRFLOW_ADMIN_USER
ARG AIRFLOW_ADMIN_PASSWORD
ARG AIRFLOW__DATABASE__SQL_ALCHEMY_CONN

# Set environment variables (Low resources configuration for development)
ENV AIRFLOW_HOME=/opt/airflow
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor
ENV AIRFLOW__WEBSERVER__WORKERS=1
ENV AIRFLOW__WEBSERVER__WEB_SERVER_MASTER_TIMEOUT=300
ENV AIRFLOW__WEBSERVER__WORKER_CLASS=gevent
ENV AIRFLOW__WEBSERVER__WEB_SERVER_PORT=7860
ENV AIRFLOW__CORE__TEST_CONNECTION='Enabled'
ENV AIRFLOW__SCHEDULER__PARSING_PROCESSES=1
ENV AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=True

# Activer le vrai système RBAC pour la gestion des utilisateurs et des rôles
ENV AIRFLOW__CORE__AUTH_MANAGER=airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager

# Switch user
USER root

# Change the UID of airflow user to 1000
RUN usermod -u 1000 airflow

# Switch back to airflow user
USER airflow

# Install any additional dependencies if needed
COPY requirements.txt requirements.txt 
RUN pip install -r requirements.txt

# COPY DAGS
COPY ./dags /opt/airflow/dags

# Expose the necessary ports (optional if Hugging Face already handles port exposure)
EXPOSE 7860

# Initialize the Airflow database (PostgreSQL in this case)
# Start Airflow webserver and scheduler within the same container
CMD ["bash", "-c", "airflow db migrate && (airflow users create --username $AIRFLOW_ADMIN_USER --firstname $AIRFLOW_ADMIN_USER --lastname $AIRFLOW_ADMIN_USER --role Admin --email ${AIRFLOW_ADMIN_USER}@sustcoop.fr --password $AIRFLOW_ADMIN_PASSWORD || echo 'User already exists') && (airflow scheduler & airflow api-server)"]
