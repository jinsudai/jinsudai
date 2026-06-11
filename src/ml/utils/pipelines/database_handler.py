"""Gestion de la base de données PostgreSQL pour les prédictions."""
import logging
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseHandler:
    """Classe de gestion de stockage des prédictions."""

    def __init__(self, db_uri=None):
        self.db_uri = db_uri

    def _get_connection(self):
        if not self.db_uri:
            raise ValueError("DB URI non fournie")
        return psycopg2.connect(self.db_uri)

    def verify_connection(self):
        if not self.db_uri:
            logger.warning("DB URI non fournie, connexion non vérifiée")
            return False
        try:
            with self._get_connection() as conn:
                conn.cursor().execute("SELECT 1")
            logger.info("Connexion à la base de données vérifiée")
            return True
        except Exception as e:
            logger.error(f"Erreur de connexion BD: {e}")
            return False

    def create_tables(self):
        if not self.db_uri:
            logger.warning("DB URI non fournie, création de table ignorée")
            return False

        create_query = """
        CREATE TABLE IF NOT EXISTS predictions_pipeline (
            prediction_id TEXT PRIMARY KEY,
            prediction_timestamp TIMESTAMP NOT NULL,
            prediction DOUBLE PRECISION NOT NULL,
            confidence DOUBLE PRECISION,
            model_version TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_query)
                    conn.commit()
            logger.info("Table predictions_pipeline créée ou déjà existante")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la création des tables: {e}")
            return False

    def store_predictions(self, df_predictions, model_version):
        if not self.db_uri:
            logger.warning("DB URI non fournie, stockage ignoré")
            return True

        if df_predictions is None or df_predictions.empty:
            logger.warning("Aucune prédiction à stocker")
            return False

        insert_query = """
        INSERT INTO predictions_pipeline (
            prediction_id, prediction_timestamp, prediction, confidence, model_version
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (prediction_id) DO NOTHING;
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    data = [
                        (
                            str(row.get("prediction_id", "")),
                            row.get("prediction_timestamp"),
                            float(row.get("prediction")),
                            float(row.get("confidence")) if row.get("confidence") is not None else None,
                            model_version,
                        )
                        for _, row in df_predictions.iterrows()
                    ]
                    execute_batch(cursor, insert_query, data)
                    conn.commit()
            logger.info(f"{len(data)} prédictions stockées")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du stockage des prédictions: {e}")
            return False

    def get_recent_predictions(self, limit=100):
        if not self.db_uri:
            logger.warning("DB URI non fournie, récupération ignorée")
            return None

        query = """
        SELECT prediction_id, prediction_timestamp, prediction, confidence, model_version, created_at
        FROM predictions_pipeline
        ORDER BY prediction_timestamp DESC
        LIMIT %s
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (limit,))
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
            return pd.DataFrame(rows, columns=columns)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des prédictions: {e}")
            return None

    def get_prediction_stats(self):
        if not self.db_uri:
            logger.warning("DB URI non fournie, statistiques ignorées")
            return None

        query = "SELECT COUNT(*) FROM predictions_pipeline"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    count = cursor.fetchone()[0]
            return {"total_predictions": count, "table_exists": True}
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {e}")
            return None
