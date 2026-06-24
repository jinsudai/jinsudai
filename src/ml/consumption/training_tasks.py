"""

Fonctions pour l'entraînement du modèle de consommation électrique.

Ce module contient les fonctions qui encapsulent l'entraînement

du modèle de consommation en utilisant les classes partagées de utils/.

Exemple d'utilisation :

    from ml.consumption.training_tasks import train_consumption_model_task

    result = train_consumption_model_task(

        features_path="data/processed/consumption_features.parquet",

        config_path="src/configs/consumption.yaml"

    )

"""

import pandas as pd

import logging

from typing import Dict, Any, Optional, List

# Importer les classes utilitaires partagées

from ml.utils.models.model import train_model, evaluate_model, get_feature_importance

from ml.utils.data.data_preparation import split_data

from ml.utils.monitoring.performance_monitor import (

    run_monitoring,

    generate_monitoring_summary

)

from ml.utils.models.models_mlflow import (

    promote_model_to_production,

    register_model_version,

    set_mlflow_tracking

)

from ml.config import load_config

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def train_consumption_model_task(

    features_path: str,

    config_path: str = "src/configs/consumption.yaml",

    test_size: Optional[float] = None,

    random_state: Optional[int] = None

) -> Dict[str, Any]:

    """

    Entraîne le modèle de consommation.

    Utilise les classes partagées de utils/ :

    - data.data_preparation.split_data

    - models.model.train_model

    - models.model.evaluate_model

    Args:

        features_path: Chemin vers le fichier Parquet des features (sortie de prepare_consumption_features)

        config_path: Chemin vers la config consommation (défaut: src/configs/consumption.yaml)

        test_size: Taille du test set (override config)

        random_state: Random state (override config)

    Returns:

        dict: Contient model, metrics, feature_importance, config utilisée

    """

    # 1. Charger la configuration

    config = load_config(config_path)

    # 2. Charger les features

    df = pd.read_parquet(features_path)

    logger.info(f"Features chargées: {df.shape[0]} lignes, {df.shape[1]} colonnes")

    # 3. Récupérer la colonne target depuis la config

    target_column = config.get('data', {}).get('target_column', 'Valeur')

    # 4. Vérifier que la colonne target existe

    if target_column not in df.columns:

        available = list(df.columns)

        raise ValueError(f"Colonne target '{target_column}' introuvable. Disponibles: {available}")

    # 5. Utiliser les utilitaires partagés pour le split

    test_size = test_size if test_size is not None else config.get('model', {}).get('test_size', 0.2)

    random_state = random_state if random_state is not None else config.get('model', {}).get('random_state', 42)

    X_train, X_test, y_train, y_test = split_data(

        df,

        test_size=test_size,

        random_state=random_state,

        target_column=target_column

    )

    logger.info(f"Split effectué: train={X_train.shape}, test={X_test.shape}")

    # 6. Entraîner le modèle (utilise la classe partagée)

    model_type = config.get('model', {}).get('model_type', 'random_forest')

    model = train_model(X_train, y_train, model_type=model_type)

    if model is None:

        raise RuntimeError("Échec de l'entraînement du modèle")

    logger.info(f"Modèle entraîné avec succès (type: {model_type})")

    # 7. Évaluer le modèle (utilise la classe partagée)

    metrics = evaluate_model(model, X_test, y_test)

    if metrics is None:

        raise RuntimeError("Échec de l'évaluation du modèle")

    logger.info(f"Métriques: {metrics}")

    # 8. Calculer l'importance des features

    feature_importance = get_feature_importance(model, list(X_train.columns), X_train=X_train)

    # 9. Retourner les résultats

    result = {

        "model": model,

        "metrics": metrics,

        "feature_importance": feature_importance,

        "config": {

            "model_type": model_type,

            "target_column": target_column,

            "test_size": test_size,

            "random_state": random_state

        },

        "data_stats": {

            "n_train": len(X_train),

            "n_test": len(X_test),

            "n_features": X_train.shape[1]

        }

    }

    logger.info("✅ Entraînement terminé avec succès")

    return result


def evaluate_consumption_model_task(

    model: Any,

    X_test: Any,

    y_test: Any,

    feature_names: Optional[List[str]] = None,

    X_train: Optional[Any] = None

) -> Dict[str, Any]:

    """

    Évalue un modèle entraîné sur des données de test.

    Utilise les classes partagées de utils/ :

    - models.model.evaluate_model

    - models.model.get_feature_importance

    Args:

        model: Modèle entraîné (sklearn, AutoGluon, etc.)

        X_test: Features de test

        y_test: Target de test

        feature_names: Liste des noms de features (optionnel)

        X_train: Features d'entraînement (requis pour AutoGluon feature importance)

    Returns:

        dict: Contient metrics et feature_importance

    """

    # 1. Évaluer le modèle (utilise la classe partagée)

    metrics = evaluate_model(model, X_test, y_test)

    if metrics is None:

        raise RuntimeError("Échec de l'évaluation du modèle")

    logger.info(f"Métriques calculées: {metrics}")

    # 2. Calculer l'importance des features

    feature_importance = None

    if feature_names:

        feature_importance = get_feature_importance(model, feature_names, X_train=X_train)

    # 3. Retourner les résultats

    result = {

        "metrics": metrics,

        "feature_importance": feature_importance

    }

    logger.info("✅ Évaluation terminée avec succès")

    return result


def evaluate_and_log_consumption_model_task(

    model: Any,

    X_test: Any,

    y_test: Any,

    config_path: str = "src/configs/consumption.yaml",

    feature_names: Optional[List[str]] = None,

    run_name: Optional[str] = None

) -> Dict[str, Any]:

    """

    Évalue un modèle ET enregistre les métriques dans MLflow.

    Args:

        model: Modèle entraîné

        X_test: Features de test

        y_test: Target de test

        config_path: Chemin vers la config consommation

        feature_names: Liste des noms de features

        run_name: Nom de la run MLflow (optionnel)

    Returns:

        dict: Contient metrics, feature_importance, mlflow_info

    """

    from ml.utils.models.models_mlflow import log_metrics, log_params

    import mlflow

    # 1. Charger config

    config = load_config(config_path)

    mlflow_config = config.get('mlflow', {})

    # 2. Configurer MLflow

    tracking_uri = mlflow_config.get('tracking_uri', 'http://localhost:5000')

    experiment_name = mlflow_config.get('experiment_name', 'energy_consumption')

    mlflow.set_tracking_uri(tracking_uri)

    mlflow.set_experiment(experiment_name)

    # 3. Démarrer une run MLflow

    with mlflow.start_run(run_name=run_name):

        # 4. Évaluer le modèle

        eval_result = evaluate_consumption_model_task(model, X_test, y_test, feature_names)

        # 5. Logger les métriques

        if eval_result["metrics"]:

            log_metrics(eval_result["metrics"])

        # 6. Logger l'importance des features

        if eval_result.get("feature_importance"):

            mlflow.log_dict(eval_result["feature_importance"], "feature_importance.json")

        # 7. Logger les params du modèle

        if hasattr(model, 'get_params'):

            log_params(dict(model.get_params()))

        # 8. Récupérer les infos de la run

        run_info = {

            "run_id": mlflow.active_run().info.run_id,

            "experiment_id": mlflow.active_run().info.experiment_id

        }

        logger.info(f"✅ Évaluation et logging terminés: {run_info['run_id']}")

    # 9. Retourner les résultats

    return {

        **eval_result,

        "mlflow": run_info

    }


def train_and_log_consumption_model_task(

    features_path: str,

    config_path: str = "src/configs/consumption.yaml"

) -> Dict[str, Any]:

    """

    Entraîne le modèle ET enregistre dans MLflow.

    Combine train_consumption_model_task avec le logging MLflow.

    Args:

        features_path: Chemin vers le fichier Parquet des features

        config_path: Chemin vers la config consommation

    Returns:

        dict: Contient model, metrics, mlflow_run_info

    """

    from ml.utils.models.models_mlflow import log_training_session

    import mlflow

    # 1. Charger config

    config = load_config(config_path)

    mlflow_config = config.get('mlflow', {})

    # 2. Configurer MLflow

    tracking_uri = mlflow_config.get('tracking_uri', 'http://localhost:5000')

    experiment_name = mlflow_config.get('experiment_name', 'energy_consumption')

    mlflow.set_tracking_uri(tracking_uri)

    mlflow.set_experiment(experiment_name)

    # 3. Démarrer une run MLflow

    with mlflow.start_run(run_name=f"consumption_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"):

        # 4. Entraîner le modèle (réutilise la tâche précédente)

        train_result = train_consumption_model_task(features_path, config_path)

        # 5. Logger avec MLflow

        log_training_session(

            model=train_result["model"],

            metrics=train_result["metrics"],

            params={

                **train_result["config"],

                "model_type": train_result["config"]["model_type"]

            },

            artifact_path="model",

            experiment_name=experiment_name,

            tracking_uri=tracking_uri

        )

        # 6. Logger l'importance des features

        if train_result.get("feature_importance"):

            mlflow.log_dict(train_result["feature_importance"], "feature_importance.json")

        # 7. Récupérer les infos de la run

        run_info = {

            "run_id": mlflow.active_run().info.run_id,

            "experiment_id": mlflow.active_run().info.experiment_id,

            "status": mlflow.active_run().info.status

        }

        logger.info(f"✅ MLflow run créée: {run_info['run_id']}")

    # 8. Retourner les résultats + infos MLflow

    return {

        **train_result,

        "mlflow": run_info

    }


def monitor_consumption_model_task(

    model: Any,

    X_train: Any,

    X_test: Any,

    y_train: Optional[Any] = None,

    y_test: Optional[Any] = None,

    feature_names: Optional[List[str]] = None,

    problem_type: Optional[str] = None

) -> Dict[str, Any]:

    """

    Effectue le monitoring complet du modèle.

    Utilise les classes partagées de utils/monitoring/ :

    - performance_monitor.run_monitoring

    - performance_monitor.detect_prediction_drift

    - performance_monitor.generate_monitoring_summary

    Args:

        model: Modèle entraîné à monitorer

        X_train: Features d'entraînement

        X_test: Features de test

        y_train: Target d'entraînement (optionnel)

        y_test: Target de test (optionnel)

        feature_names: Liste des noms de features (optionnel)

        problem_type: Type de problème ('regression' ou 'classification')

    Returns:

        dict: Contient drift_results, performance_train, performance_test, summary

    """

    # 1. Exécuter le monitoring complet

    monitoring_results = run_monitoring(

        model=model,

        X_train=X_train,

        X_test=X_test,

        y_train=y_train,

        y_test=y_test,

        feature_names=feature_names,

        problem_type=problem_type

    )

    if monitoring_results is None:

        raise RuntimeError("Échec du monitoring du modèle")

    # 2. Générer un résumé

    summary = generate_monitoring_summary(monitoring_results)

    logger.info(f"\n{summary}")

    # 3. Retourner les résultats

    result = {

        "drift": monitoring_results.get("drift"),

        "performance_train": monitoring_results.get("performance_train"),

        "performance_test": monitoring_results.get("performance_test"),

        "problem_type": monitoring_results.get("problem_type"),

        "summary": summary

    }

    # 4. Logger un avertissement si drift détecté

    if result["drift"] and result["drift"].get("drift_detected"):

        logger.warning("⚠️ DRIFT DÉTECTÉ ! Vérifiez les performances du modèle.")

    logger.info("✅ Monitoring terminé avec succès")

    return result


def monitor_and_log_consumption_model_task(

    model: Any,

    X_train: Any,

    X_test: Any,

    y_train: Optional[Any] = None,

    y_test: Optional[Any] = None,

    config_path: str = "src/configs/consumption.yaml",

    feature_names: Optional[List[str]] = None,

    run_name: Optional[str] = None

) -> Dict[str, Any]:

    """

    Monitoring + logging dans MLflow.

    Args:

        model: Modèle entraîné

        X_train: Features d'entraînement

        X_test: Features de test

        y_train: Target d'entraînement (optionnel)

        y_test: Target de test (optionnel)

        config_path: Chemin vers la config consommation

        feature_names: Liste des noms de features

        run_name: Nom de la run MLflow

    Returns:

        dict: Contient monitoring_results + mlflow_info

    """

    from ml.utils.models.models_mlflow import log_metrics, log_params

    import mlflow

    # 1. Charger config

    config = load_config(config_path)

    mlflow_config = config.get('mlflow', {})

    # 2. Configurer MLflow

    tracking_uri = mlflow_config.get('tracking_uri', 'http://localhost:5000')

    experiment_name = mlflow_config.get('experiment_name', 'energy_consumption')

    mlflow.set_tracking_uri(tracking_uri)

    mlflow.set_experiment(experiment_name)

    # 3. Démarrer une run MLflow

    with mlflow.start_run(run_name=run_name):

        # 4. Exécuter le monitoring

        monitor_result = monitor_consumption_model_task(

            model=model,

            X_train=X_train,

            X_test=X_test,

            y_train=y_train,

            y_test=y_test,

            feature_names=feature_names

        )

        # 5. Logger les métriques de monitoring

        if monitor_result.get("drift"):

            drift_metrics = {

                "monitoring_drift_detected": int(monitor_result["drift"]["drift_detected"]),

                "monitoring_mean_drift": monitor_result["drift"]["mean_drift"],

                "monitoring_std_drift": monitor_result["drift"]["std_drift"]

            }

            log_metrics(drift_metrics)

        if monitor_result.get("performance_test"):

            log_metrics({

                f"monitoring_test_{k}": v

                for k, v in monitor_result["performance_test"].items()

            })

        if monitor_result.get("performance_train"):

            log_metrics({

                f"monitoring_train_{k}": v

                for k, v in monitor_result["performance_train"].items()

            })

        # 6. Logger le problème type

        if monitor_result.get("problem_type"):

            log_params({"monitoring_problem_type": monitor_result["problem_type"]})

        # 7. Récupérer les infos de la run

        run_info = {

            "run_id": mlflow.active_run().info.run_id,

            "experiment_id": mlflow.active_run().info.experiment_id

        }

        logger.info(f"✅ Monitoring et logging terminés: {run_info['run_id']}")

    # 8. Retourner les résultats

    return {

        **monitor_result,

        "mlflow": run_info

    }


def stage_consumption_model_task(

    model: Any,

    config_path: str = "src/configs/consumption.yaml",

    run_id: Optional[str] = None,

    metric_keys: Optional[List[str]] = None,

    min_improvement: float = 0.0,

    promote_to_prod: bool = True

) -> Dict[str, Any]:

    """

    Enregistre le modèle dans MLflow Model Registry et gère les stages.

    Utilise les classes partagées de utils/models/mlflow_tracker.py :

    - register_model_version

    - promote_model_to_production

    - get_model_version_by_alias

    - set_mlflow_tracking

    - get_mlflow_config

    Args:

        model: Modèle entraîné à enregistrer

        config_path: Chemin vers la config consommation

        run_id: ID de la run MLflow (optionnel, sinon utilise la dernière)

        metric_keys: Liste des métriques pour la comparaison (ex: ["mae", "rmse"])

        min_improvement: Amélioration minimale requise en % pour la promotion

        promote_to_prod: Si True, tente la promotion automatique vers Production

    Returns:

        dict: Contient version, alias, promotion_result, model_uri

    """

    import mlflow

    # 1. Charger config

    config = load_config(config_path)

    mlflow_config = config.get('mlflow', {})

    model_name = mlflow_config.get('model_name', 'consumption_model')

    # 2. Configurer MLflow

    tracking_uri = mlflow_config.get('tracking_uri', 'http://localhost:5000')

    experiment_name = mlflow_config.get('experiment_name', 'energy_consumption')

    set_mlflow_tracking(tracking_uri)

    mlflow.set_experiment(experiment_name)

    # 3. Définir les métriques par défaut pour la consommation (régression)

    if metric_keys is None:

        metric_keys = ["mae", "rmse", "r2"]

    # 4. Enregistrer le modèle dans Model Registry

    model_version = register_model_version(

        model_name=model_name,

        run_id=run_id,

        artifact_path="model"

    )

    if model_version is None:

        raise RuntimeError("Échec de l'enregistrement de la version du modèle")

    version = int(model_version.version)

    logger.info(f"✅ Modèle enregistré: {model_name} v{version}")

    # 5. Vérifier la version Production actuelle

    # prod_version = get_model_version_by_alias(model_name, "prod")

    # 6. Promotion vers Production (si demandé)

    promotion_result = None

    if promote_to_prod:

        promotion_result = promote_model_to_production(

            model_name=model_name,

            version=version,

            alias_prod="prod",

            metric_keys=metric_keys,

            min_improvement=min_improvement

        )

        if promotion_result['success']:

            logger.info(f"✅ Modèle promu vers Production: {model_name} v{version}")

        else:

            logger.warning(f"⚠️ Modèle NON promu: {promotion_result['reason']}")

    # 7. Construire le model URI

    model_uri = f"models:/{model_name}/staging" if not promote_to_prod else f"models:/{model_name}/prod"

    # 8. Retourner les résultats

    return {

        "model_name": model_name,

        "version": version,

        "alias": "prod" if promote_to_prod and promotion_result and promotion_result['success'] else "staging",

        "model_uri": model_uri,

        "promotion": promotion_result,

        "tracking_uri": tracking_uri

    }


def stage_and_log_consumption_model_task(

    model: Any,

    run_id: Optional[str] = None,

    config_path: str = "src/configs/consumption.yaml",

    metric_keys: Optional[List[str]] = None,

    min_improvement: float = 0.0

) -> Dict[str, Any]:

    """

    Staging complet + logging dans MLflow.

    Combine :

    1. Enregistrement dans Model Registry

    2. Promotion vers Production

    3. Logging des infos dans MLflow

    Args:

        model: Modèle entraîné

        run_id: ID de la run MLflow

        config_path: Chemin vers la config consommation

        metric_keys: Métriques pour la comparaison

        min_improvement: Amélioration minimale requise

    Returns:

        dict: Contient staging_info + mlflow_info

    """

    import mlflow

    from ml.utils.models.models_mlflow import log_params, log_model

    # 1. Charger config

    config = load_config(config_path)

    mlflow_config = config.get('mlflow', {})

    # 2. Configurer MLflow

    tracking_uri = mlflow_config.get('tracking_uri', 'http://localhost:5000')

    experiment_name = mlflow_config.get('experiment_name', 'energy_consumption')

    set_mlflow_tracking(tracking_uri)

    mlflow.set_experiment(experiment_name)

    # 3. Démarrer une run MLflow pour le logging

    with mlflow.start_run(run_name=f"staging_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"):

        # 4. Enregistrer et staging

        staging_result = stage_consumption_model_task(

            model=model,

            config_path=config_path,

            run_id=run_id,

            metric_keys=metric_keys,

            min_improvement=min_improvement

        )

        # 5. Logger les infos de staging

        log_params({

            "model_name": staging_result["model_name"],

            "model_version": staging_result["version"],

            "model_alias": staging_result["alias"],

            "promoted_to_prod": staging_result["promotion"]["success"] if staging_result["promotion"] else False

        })

        # 6. Logger le modèle

        log_model(model, artifact_path="model")

        # 7. Récupérer les infos de la run

        run_info = {

            "run_id": mlflow.active_run().info.run_id,

            "experiment_id": mlflow.active_run().info.experiment_id

        }

        logger.info(f"✅ Staging et logging terminés: {run_info['run_id']}")

    # 8. Retourner les résultats

    return {

        **staging_result,

        "mlflow": run_info

    }

