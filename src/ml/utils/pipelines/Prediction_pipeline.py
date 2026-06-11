"""
Pipeline complet d'inférence en production : chargement modèle -> validation données -> prédictions -> stockage/notifications.

Spécifications (voir SPECIFICATIONS.md) :
- Étapes :
  1. Chargement modèle : Depuis MLflow
  2. Validation données : Vérification schéma, ranges
  3. Génération features : Préparation identique à training
  4. Inférence : Prédiction kWh (consommation ou production PV)
  5. Stockage : BD ou CSV
  6. Alertes : Notif si dérive ou seuil métier dépassé

- Performance : < 100ms par requête
- Input : Features PRM, météo et calendrier
- Output : Valeur prédite en kWh

Classe principale :
- PredictionPipeline : Orchestration complète du cycle prédiction
"""
import logging
from datetime import datetime

from ml.utils.data.data_transformer import clean_data
from ..models.inference_model import InferenceModel
from .data_generator import generate_inference_data, prepare_features_for_model, add_predictions_to_data
from .database_handler import DatabaseHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionPipeline:
    """Pipeline complet pour l'inférence et le stockage des prédictions"""
    
    def __init__(self, mlflow_uri, experiment_name, db_uri):
        """
        Initialise le pipeline
        
        Args:
            mlflow_uri: URI du serveur MLflow
            experiment_name: Nom de l'expérience MLflow
            db_uri: URI de connexion PostgreSQL
        """
        self.mlflow_uri = mlflow_uri
        self.experiment_name = experiment_name
        self.db_uri = db_uri
        
        self.inference_model = None
        self.db_handler = None
        self.df_inference = None
        self.df_predictions = None
        
        logger.info("Pipeline d'inférence initialisé")
    
    def setup(self):
        """Configure le pipeline (MLflow + BD)"""
        logger.info("=== ÉTAPE 1: CONFIGURATION ===")
        
        # Initialiser MLflow
        self.inference_model = InferenceModel(self.mlflow_uri, self.experiment_name)
        logger.info("MLflow configuré")
        
        # Initialiser BD si l'URI est fournie
        if self.db_uri:
            self.db_handler = DatabaseHandler(self.db_uri)
            if not self.db_handler.verify_connection():
                logger.error("Impossible de se connecter à la base de données")
                return False
            if not self.db_handler.create_tables():
                logger.error("Impossible de créer les tables")
                return False
            logger.info("Base de données configurée")
        else:
            logger.warning("Aucune URI de base de données fournie : stockage des prédictions désactivé")
            self.db_handler = DatabaseHandler(None)
        
        return True
    
    def load_model(self, model_name, alias_prod="prod"):
        """
        Charge le modèle en production via Alias
        
        Args:
            model_name: Nom du modèle dans MLflow
            alias_prod: Alias pour la production (défaut: "prod")
            
        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 2: CHARGEMENT DU MODÈLE ===")
        
        if not self.inference_model.load_production_model(model_name, alias_prod=alias_prod):
            logger.error(f"Impossible de charger le modèle {model_name} avec l'alias '{alias_prod}'")
            return False
        
        model_info = self.inference_model.get_model_info()
        logger.info(f"Modèle chargé: {model_info}")
        return True

    def get_model_info(self):
        """Retourne les informations du modèle chargé via le pipeline."""
        if self.inference_model is None:
            logger.error("Aucun modèle chargé dans le pipeline")
            return None
        return self.inference_model.get_model_info()
    
    def generate_data(self, n_days=3, n_samples_per_day=24, feature_columns=None):
        """
        Génère les données d'inférence
        
        Args:
            n_days: Nombre de jours
            n_samples_per_day: Nombre d'échantillons par jour
            feature_columns: Liste des colonnes features
            
        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 3: GÉNÉRATION DES DONNÉES ===")
        
        self.df_inference = generate_inference_data(
            n_days=n_days,
            n_samples_per_day=n_samples_per_day,
            feature_columns=feature_columns
        )
        
        if self.df_inference is None or len(self.df_inference) == 0:
            logger.error("Impossible de générer les données d'inférence")
            return False
        
        logger.info(f"df_inference généré avec succès: {self.df_inference.head()}")

        return True

    def set_inference_data(self, df_inference):
        """Charge un DataFrame d'inférence existant dans le pipeline."""
        if df_inference is None or df_inference.empty:
            logger.error("Le DataFrame d'inférence est vide ou None")
            return False
        self.df_inference = df_inference.copy()
        logger.info(f"DataFrame d'inférence chargé: {self.df_inference.shape}")
        return True

    def prepare_features(self):
        """Prépare les features à partir du DataFrame d'inférence."""
        if self.df_inference is None or self.df_inference.empty:
            logger.error("Pas de données d'inférence chargées")
            return None, None
        self.df_features = clean_data(self.df_inference)

        if self.df_features is None:
            logger.error("Impossible de préparer les features")
            return None, None

        return self.df_features
    
    def run_predictions(self, feature_columns=None):
        """
        Exécute les prédictions
        
        Args:
            feature_columns: Liste des colonnes features pour le modèle
            
        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 4: EXÉCUTION DES PRÉDICTIONS ===")
        
        if self.df_inference is None:
            logger.error("Données d'inférence non générées")
            return False
        
        # Préparer les features
        #X_inference, timestamps = prepare_features_for_model(self.df_inference, feature_columns)
        
        #if self.df_inference is None:
        #    logger.error("Impossible de préparer les features")
        #    return False
        
        # Générer les prédictions
        predictions, confidence_scores = self.inference_model.predict(self.df_inference)
        
        if predictions is None:
            logger.error("Impossible de générer les prédictions")
            return False
        
        # Ajouter les prédictions aux données
        self.df_predictions = add_predictions_to_data(
            self.df_inference,
            predictions,
            confidence_scores
        )
        
        logger.info(f"Prédictions générées: {len(self.df_predictions)} échantillons")
        return True
    
    def store_predictions(self):
        """
        Stocke les prédictions en base de données
        
        Returns:
            True si succès, False sinon
        """
        logger.info("=== ÉTAPE 5: STOCKAGE EN BASE DE DONNÉES ===")
        
        if self.df_predictions is None:
            logger.error("Pas de prédictions à stocker")
            return False
        
        # S'assurer que la colonne prediction_timestamp est disponible
        if 'prediction_timestamp' not in self.df_predictions.columns:
            if 'horodate' in self.df_predictions.columns:
                self.df_predictions['prediction_timestamp'] = self.df_predictions['horodate']
            elif 'timestamp' in self.df_predictions.columns:
                self.df_predictions['prediction_timestamp'] = self.df_predictions['timestamp']
            else:
                logger.warning("Aucune colonne de timestamp valide trouvée pour le stockage, utilisation de l'heure actuelle")
                self.df_predictions['prediction_timestamp'] = datetime.now()

        model_info = self.inference_model.get_model_info()
        model_version = model_info['version'] if model_info else 'unknown'
        
        if not self.db_handler.store_predictions(self.df_predictions, model_version):
            logger.error("Impossible de stocker les prédictions")
            return False
        
        logger.info("Prédictions stockées avec succès")
        return True
    
    def verify_results(self):
        """
        Vérifie les résultats du pipeline
        
        Returns:
            DataFrame des prédictions récentes ou None
        """
        logger.info("=== ÉTAPE 6: VÉRIFICATION DES RÉSULTATS ===")
        
        stats = self.db_handler.get_prediction_stats()
        logger.info(f"Statistiques BD: {stats}")
        
        recent_predictions = self.db_handler.get_recent_predictions(limit=10)
        
        if recent_predictions is not None:
            logger.info(f"Prédictions récentes:\n{recent_predictions.to_string()}")
        
        return recent_predictions
    
    def run_full_pipeline(self, model_name, feature_columns, n_days=3, n_samples_per_day=24, alias_prod="prod"):
        """
        Exécute le pipeline complet
        
        Args:
            model_name: Nom du modèle dans MLflow
            feature_columns: Liste des colonnes features
            n_days: Nombre de jours de prédictions
            n_samples_per_day: Nombre d'échantillons par jour
            alias_prod: Alias pour la production (défaut: "prod")
            
        Returns:
            Tuple (succès: bool, DataFrame des prédictions ou None)
        """
        logger.info("####################################################")
        logger.info("### PIPELINE COMPLET D'INFÉRENCE EN PRODUCTION ###")
        logger.info(f"### Date/Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ###")
        logger.info("####################################################\n")
        
        # Exécuter chaque étape
        if not self.setup():
            return False, None
        
        if not self.load_model(model_name, alias_prod=alias_prod):
            return False, None
        
        if not self.generate_data(n_days=n_days, n_samples_per_day=n_samples_per_day, feature_columns=feature_columns):
            return False, None
        
        if not self.run_predictions(feature_columns):
            return False, None
        
        if not self.store_predictions():
            return False, None
        
        results = self.verify_results()
        
        logger.info("\n####################################################")
        logger.info("### PIPELINE TERMINÉ AVEC SUCCÈS ###")
        logger.info("####################################################\n")
        
        return True, results
    
    def get_predictions_df(self):
        """Retourne le DataFrame des prédictions générées"""
        return self.df_predictions
