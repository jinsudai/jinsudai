"""Gestion de la base de données PostgreSQL pour les prédictions."""

import logging

import pandas as pd

import psycopg2

import uuid

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

            prediction_id UUID PRIMARY KEY,

            prediction_timestamp TIMESTAMP NOT NULL,

            prediction_index INTEGER NOT NULL,

            prediction DOUBLE PRECISION NOT NULL,

            model_version TEXT NOT NULL,

            entity_id TEXT NOT NULL,

            run_id TEXT NOT NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            actual_value DOUBLE PRECISION

        );

        """



        try:

            with self._get_connection() as conn:

                with conn.cursor() as cursor:

                    cursor.execute(create_query)

                    cursor.execute(

                        "CREATE INDEX IF NOT EXISTS idx_predictions_pipeline_prediction_timestamp ON predictions_pipeline (prediction_timestamp);"

                    )

                    cursor.execute(

                        "CREATE INDEX IF NOT EXISTS idx_predictions_pipeline_prediction_index ON predictions_pipeline (prediction_index);"

                    )

                    cursor.execute(

                        "CREATE INDEX IF NOT EXISTS idx_predictions_pipeline_entity_id ON predictions_pipeline (entity_id);"

                    )

                    cursor.execute(

                        "CREATE INDEX IF NOT EXISTS idx_predictions_pipeline_run_id ON predictions_pipeline (run_id);"

                    )

                    # Créer une vue avec ordre par défaut décroissant sur prediction_timestamp

                    cursor.execute("""

                        CREATE OR REPLACE VIEW predictions_pipeline_sorted AS

                        SELECT * FROM predictions_pipeline

                        ORDER BY prediction_timestamp DESC;

                    """)

                    conn.commit()

            logger.info("Table predictions_pipeline créée ou déjà existante")

            return True

        except Exception as e:

            logger.error(f"Erreur lors de la création des tables: {e}")

            return False



    def store_predictions(self, df_predictions, model_version, run_id=None):

        if not self.db_uri:

            logger.warning("DB URI non fournie, stockage ignoré")

            return True



        if df_predictions is None or df_predictions.empty:

            logger.warning("Aucune prédiction à stocker")

            return False



        df = df_predictions.copy()



        if 'prediction_timestamp' not in df.columns:

            if 'horodate' in df.columns:

                df['prediction_timestamp'] = pd.to_datetime(df['horodate'])

            elif 'timestamp' in df.columns:

                df['prediction_timestamp'] = pd.to_datetime(df['timestamp'])

            else:

                df['prediction_timestamp'] = pd.Timestamp.now()



        if 'prediction_index' not in df.columns:

            df = df.reset_index(drop=True)

            df['prediction_index'] = df.index + 1



        insert_query = """

        INSERT INTO predictions_pipeline (

            prediction_id, prediction_timestamp, prediction_index, prediction, model_version, entity_id, run_id

        ) VALUES (%s, %s, %s, %s, %s, %s, %s)

        ON CONFLICT (prediction_id) DO NOTHING;

        """



        try:

            with self._get_connection() as conn:

                with conn.cursor() as cursor:

                    data = [

                        (

                            str(uuid.uuid4()),

                            row.get("prediction_timestamp"),

                            int(row.get("prediction_index", 0)),

                            float(row.get("prediction")),

                            model_version,

                            "550e8400-e29b-41d4-a716-446655440000",

                            run_id if run_id else "6ba7b810-9dad-11d1-80b4-00c04fd430c8",

                        )

                        for _, row in df.iterrows()

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

        SELECT prediction_id, prediction_timestamp, prediction, model_version, entity_id, run_id, created_at

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



    def get_predictions_by_date(self, start_date, end_date):

        """

        Récupère les prédictions pour une plage de dates



        Args:

            start_date: Date de début (datetime ou string)

            end_date: Date de fin (datetime ou string)



        Returns:

            DataFrame des prédictions ou None

        """

        if not self.db_uri:

            logger.warning("DB URI non fournie, récupération ignorée")

            return None



        query = """

        SELECT prediction_id, prediction_timestamp, prediction_index,

               prediction, model_version, entity_id, run_id, actual_value

        FROM predictions_pipeline

        WHERE prediction_timestamp >= %s AND prediction_timestamp <= %s

        ORDER BY prediction_timestamp DESC

        """



        try:

            with self._get_connection() as conn:

                with conn.cursor() as cursor:

                    cursor.execute(query, (start_date, end_date))

                    rows = cursor.fetchall()

                    columns = [desc[0] for desc in cursor.description]

            return pd.DataFrame(rows, columns=columns)

        except Exception as e:

            logger.error(f"Erreur lors de la récupération des prédictions par date: {e}")

            return None



    def update_actual_values(self, prediction_ids, actual_values):

        """

        Met à jour les valeurs réelles pour les prédictions données



        Args:

            prediction_ids: Liste des IDs de prédictions à mettre à jour

            actual_values: Liste des valeurs réelles correspondantes



        Returns:

            True si succès, False sinon

        """

        if not self.db_uri:

            logger.warning("DB URI non fournie, mise à jour ignorée")

            return False



        if len(prediction_ids) != len(actual_values):

            logger.error("Les listes prediction_ids et actual_values doivent avoir la même longueur")

            return False



        update_query = """

        UPDATE predictions_pipeline

        SET actual_value = %s

        WHERE prediction_id = %s

        """



        try:

            with self._get_connection() as conn:

                with conn.cursor() as cursor:

                    data = [(actual_value, pred_id) for pred_id, actual_value in zip(prediction_ids, actual_values)]

                    execute_batch(cursor, update_query, data)

                    conn.commit()

            logger.info(f"{len(data)} prédictions mises à jour avec les valeurs réelles")

            return True

        except Exception as e:

            logger.error(f"Erreur lors de la mise à jour des valeurs réelles: {e}")

            return False



    def add_actual_value_column(self):

        """

        Ajoute la colonne actual_value si elle n'existe pas déjà



        Returns:

            True si succès ou colonne existe déjà, False sinon

        """

        if not self.db_uri:

            logger.warning("DB URI non fournie, ajout de colonne ignoré")

            return False



        alter_query = """

        ALTER TABLE predictions_pipeline

        ADD COLUMN IF NOT EXISTS actual_value DOUBLE PRECISION

        """



        try:

            with self._get_connection() as conn:

                with conn.cursor() as cursor:

                    cursor.execute(alter_query)

                    conn.commit()

            logger.info("Colonne actual_value ajoutée ou déjà existante")

            return True

        except Exception as e:

            logger.error(f"Erreur lors de l'ajout de la colonne actual_value: {e}")

            return False









    def get_production_data_for_retraining(self, limit=None):

        """

        Récupère les données de production avec valeurs réelles pour le retraining.



        Args:

            limit: Nombre maximum d'enregistrements (optionnel)



        Returns:

            DataFrame avec les colonnes prediction_timestamp, prediction, actual_value

            ou None en cas d'erreur

        """

        if not self.db_uri:

            logger.warning("DB URI non fournie, récupération des données de production ignorée")

            return None



        if limit:

            query = """

            SELECT prediction_timestamp, prediction, actual_value

            FROM predictions_pipeline

            WHERE actual_value IS NOT NULL

            ORDER BY prediction_timestamp DESC

            LIMIT %s

            """

            params = (limit,)

        else:

            query = """

            SELECT prediction_timestamp, prediction, actual_value

            FROM predictions_pipeline

            WHERE actual_value IS NOT NULL

            ORDER BY prediction_timestamp DESC

            """

            params = ()



        try:

            with self._get_connection() as conn:

                with conn.cursor() as cursor:

                    cursor.execute(query, params)

                    rows = cursor.fetchall()

                    columns = [desc[0] for desc in cursor.description]

            df = pd.DataFrame(rows, columns=columns)

            logger.info(f"Données de production récupérées: {len(df)} enregistrements")

            return df

        except Exception as e:

            logger.error(f"Erreur lors de la récupération des données de production: {e}")

            return None

