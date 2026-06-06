"""
Entraînement et gestion du modèle.

Spécifications (voir SPECIFICATIONS.md) :
- Modèle : Régression (consommation ou production PV en kWh)
- Métriques cibles : R², MAE, RMSE (seuils par domaine dans config)
- Algorithmes supportés : RandomForest, Autogluon
- Input : DataFrame features PRM, météo et calendrier
- Output : Modèle versionné dans MLflow + métriques
- Performance : Entraînement < 1h, Inférence < 100ms

Fonctions principales :
- train_model() : Entraîne le modèle
- Metrics : R², MAE, RMSE (régression) ; métriques classification si problem_type adapté
"""
import logging
from turtle import pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.metrics import mean_squared_error, r2_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def train_model(X_train, y_train, model_type="random_forest", **kwargs):
    try:
        logger.info(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")

        if X_train.shape[0] == 0 or len(y_train) == 0:
            logger.error("Données vides")
            return None

        # -----------------------
        # RANDOM FOREST / SKLEARN
        # -----------------------
        if model_type == "random_forest":
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

            unique_values = len(set(y_train))
            if unique_values < 20:
                model = RandomForestClassifier(
                    n_estimators=kwargs.get('n_estimators', 100),
                    random_state=kwargs.get('random_state', 42),
                    n_jobs=-1
                )
            else:
                model = RandomForestRegressor(
                    n_estimators=kwargs.get('n_estimators', 100),
                    random_state=kwargs.get('random_state', 42),
                    n_jobs=-1
                )

            model.fit(X_train, y_train)
            return model

        # -----------------------
        # LINEAR REGRESSION
        # -----------------------
        if model_type == "linear_regression":
            from sklearn.linear_model import LinearRegression
            model = LinearRegression()
            model.fit(X_train, y_train)
            return model

        # -----------------------
        # AUTOGLUON
        # -----------------------
        if model_type == "auto_gluon":
            import pandas as pd
            from autogluon.tabular import TabularPredictor

            train_data = pd.DataFrame(X_train).copy()
            train_data["target"] = y_train.values

            predictor = TabularPredictor(label="target").fit(
                train_data,
                presets="good",
                num_bag_folds=0,
                num_stack_levels=0
            )

            return predictor

        logger.error(f"Type de modèle non supporté: {model_type}")
        return None

    except Exception as e:
        logger.error(f"Erreur lors de l'entraînement: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def evaluate_model(model, X_test, y_test):
    """
    Évalue les performances du modèle
    
    Args:
        model: Modèle entraîné (sklearn, Autogluon, etc.)
        X_test: Features de test
        y_test: Target de test
    
    Returns:
        dict: Métriques d'évaluation
    """
    try:
        # ----------------------
        # AUTOGLUON
        # ----------------------
        if type(model).__name__ == 'TabularPredictor':
            import pandas as pd
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

            # Préparer les données de test
            X_test_df = pd.DataFrame(X_test).copy()
            test_data = X_test_df.copy()
            test_data['target'] = y_test.values

            # Essayer d'utiliser l'évaluation AutoGluon, mais vérifier manuellement les métriques
            metrics = {}
            try:
                metrics = model.evaluate(test_data, silent=True)
            except TypeError:
                metrics = model.evaluate(test_data)
            except Exception as e:
                logger.warning(f"Évaluation AutoGluon via evaluate() a échoué: {e}")

            # Calcul manuel pour vérifier le résultat et éviter les métriques trompeuses
            try:
                predictions = model.predict(X_test_df)
                metrics['accuracy_manual'] = accuracy_score(y_test, predictions)
                metrics['precision_manual'] = precision_score(y_test, predictions, average='binary', zero_division=0)
                metrics['recall_manual'] = recall_score(y_test, predictions, average='binary', zero_division=0)
                metrics['f1_manual'] = f1_score(y_test, predictions, average='binary', zero_division=0)
            except Exception as e:
                logger.warning(f"Calcul manuel des métriques AutoGluon a échoué: {e}")

            logger.info(f"Autogluon - Métriques: {metrics}")
            return metrics
        
        # ----------------------
        # SKLEARN
        # ----------------------
        predictions = model.predict(X_test)
        metrics = {}
        
        # Vérifier si classification ou régression
        if hasattr(model, 'predict_proba'):  # Classification
            metrics['accuracy'] = accuracy_score(y_test, predictions)
            metrics['precision'] = precision_score(y_test, predictions, average='weighted', zero_division=0)
            metrics['recall'] = recall_score(y_test, predictions, average='weighted', zero_division=0)
            metrics['f1'] = f1_score(y_test, predictions, average='weighted', zero_division=0)
            logger.info(f"Classification - Accuracy: {metrics['accuracy']:.3f}, F1: {metrics['f1']:.3f}")
        else:  # Régression
            metrics['mse'] = mean_squared_error(y_test, predictions)
            metrics['rmse'] = metrics['mse'] ** 0.5
            metrics['r2'] = r2_score(y_test, predictions)
            logger.info(f"Régression - RMSE: {metrics['rmse']:.3f}, R²: {metrics['r2']:.3f}")
        
        return metrics
    except Exception as e:
        logger.error(f"Erreur lors de l'évaluation: {e}")
        return None


# Note: Sauvegarde du modèle gérée par MLflow avec mlflow.sklearn.log_model()
# Voir mlflow_tracker.py pour les détails


def get_feature_importance(model, feature_names=None, X_train=None):
    """
    Obtient l'importance des features
    
    Args:
        model: Modèle entraîné (sklearn ou AutoGluon TabularPredictor)
        feature_names: Liste des noms de features (optionnel)
        X_train: Données d'entraînement (requis pour AutoGluon)
    """
    try:
        # ----------------------
        # AUTOGLUON
        # ----------------------
        if type(model).__name__ == 'TabularPredictor':
            # Autogluon récupère l'importance via feature_importance()
            # Requiert un dataset pour calculer l'importance
            if X_train is not None:
                importance_dict = model.feature_importance(X_train)
                logger.info("Feature importances calculées (Autogluon)")
                return importance_dict
            else:
                logger.warning("X_train requis pour calculer feature_importance avec AutoGluon")
                return None
        
        # ----------------------
        # SKLEARN
        # ----------------------
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            
            if feature_names is None:
                feature_names = [f"Feature_{i}" for i in range(len(importances))]
            
            # Créer un dictionnaire trié
            importance_dict = {name: imp for name, imp in zip(feature_names, importances)}
            importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            
            logger.info("Features importances calculées")
            return importance_dict
        else:
            logger.warning("Le modèle n'a pas d'attribut 'feature_importances_'")
            return None
    except Exception as e:
        logger.error(f"Erreur lors du calcul des importances: {e}")
        return None
