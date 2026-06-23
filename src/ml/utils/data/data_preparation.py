"""

Préparation et prétraitement des données.



Spécifications (voir SPECIFICATIONS.md) :

- Étapes : Détection types, imputation, scaling, encoding

- Valeurs manquantes : Imputation (stratégie TBD)

- Normalisation : StandardScaler sur features numériques

- Encoding : OneHotEncoder si variables catégoriques

- Train/Test split : Stratifié si classification



Inclut : détection auto des types, imputation, scaling, encoding

"""

import pandas as pd

import numpy as np

import logging

from sklearn.pipeline import Pipeline

from sklearn.impute import SimpleImputer

from sklearn.preprocessing import StandardScaler, OneHotEncoder

from sklearn.compose import ColumnTransformer



from ml.utils.data.data_transformer import transform_date_columns



logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)





def detect_feature_types(X):

    """

    Détecte automatiquement les colonnes numériques et catégories



    Args:

        X: DataFrame avec les features



    Returns:

        tuple: (numeric_features, categorical_features)

    """

    numeric_features = []

    categorical_features = []



    for col, dtype in X.dtypes.items():

        if ('float' in str(dtype)) or ('int' in str(dtype)):

            numeric_features.append(col)

        else:

            categorical_features.append(col)



    logger.info(f"🔍 Features numériques détectées: {numeric_features}")

    logger.info(f"🔍 Features catégories détectées: {categorical_features}")



    return numeric_features, categorical_features





def create_preprocessor(numeric_features, categorical_features):

    """

    Crée un preprocessor avec pipelines pour données numériques et catégories



    Args:

        numeric_features: Liste des colonnes numériques

        categorical_features: Liste des colonnes catégories



    Returns:

        ColumnTransformer: Preprocessor configuré

    """

    # Pipeline pour features numériques

    numeric_transformer = Pipeline(steps=[

        ('imputer', SimpleImputer(strategy='mean')),

        ('scaler', StandardScaler())

    ])

    logger.info("✓ Pipeline numériques créé: Imputer(mean) + Scaler")



    # Pipeline pour features catégories

    categorical_transformer = Pipeline(steps=[

        ('encoder', OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore'))

    ])

    logger.info("✓ Pipeline catégories créé: OneHotEncoder")



    # ColumnTransformer pour combiner les deux

    preprocessor = ColumnTransformer(

        transformers=[

            ('num', numeric_transformer, numeric_features),

            ('cat', categorical_transformer, categorical_features)

        ],

        remainder='drop'  # Ignorer les colonnes non listées

    )

    logger.info("✓ ColumnTransformer créé")



    return preprocessor





def get_feature_names(preprocessor, numeric_features, categorical_features):

    """

    Récupère les noms des colonnes après transformation



    Args:

        preprocessor: ColumnTransformer configuré et fitted

        numeric_features: Liste des features numériques

        categorical_features: Liste des features catégories



    Returns:

        list: Noms des colonnes transformées

    """

    feature_names = []



    # Features numériques (inchangées)

    feature_names.extend(numeric_features)



    # Features catégories (encodées)

    if categorical_features:

        try:

            encoder = None

            if hasattr(preprocessor, 'named_transformers_'):

                cat_transformer = preprocessor.named_transformers_.get('cat')

                if hasattr(cat_transformer, 'named_steps'):

                    encoder = cat_transformer.named_steps.get('encoder')

                elif hasattr(cat_transformer, 'get_feature_names_out'):

                    encoder = cat_transformer

            elif hasattr(preprocessor, 'named_steps'):

                encoder = preprocessor.named_steps['cat'].named_steps['encoder']



            if encoder is not None:

                cat_names = encoder.get_feature_names_out(categorical_features)

                feature_names.extend(cat_names)

            else:

                raise AttributeError("Impossible de localiser l'encodeur de colonnes catégorielles")

        except Exception as e:

            logger.warning(f"Impossible de récupérer les noms de features catégories: {e}")



    return feature_names





def prepare_data(X_train, X_test, numeric_features=None, categorical_features=None, autogluon=False):

    """

    Prépare les données: détection auto des types, création et application du preprocessor



    Args:

        X_train: Features d'entraînement

        X_test: Features de test

        numeric_features: Optionnel, liste des features numériques (auto-détection si None)

        categorical_features: Optionnel, liste des features catégories (auto-détection si None)

        autogluon: bool, si True retourne des DataFrames bruts pour AutoGluon



    Returns:

        dict: Contenant X_train_transformed / X_train, X_test_transformed / X_test,

              preprocessor, feature_names, numeric_features, categorical_features

    """

    logger.info("=== PRÉPARATION DES DONNÉES ===")



    # Détection automatique si non fourni

    if numeric_features is None or categorical_features is None:

        logger.info("\n1️⃣ Détection des types de features...________")

        num_features, cat_features = detect_feature_types(X_train)

        if numeric_features is None:

            numeric_features = num_features

        if categorical_features is None:

            categorical_features = cat_features



    # Si mode AutoGluon : limiter le prétraitement et renvoyer des DataFrames

    if autogluon:

        logger.info("\n2️⃣ AutoGluon mode — prétraitement minimal...")



        # Copies pour ne pas muter les originaux

        X_train_p = X_train.copy()

        X_test_p = X_test.copy()



        # Transformer colonnes date si présentes (Dejà fait pretraitement stateless?)

        # X_train_p = transform_date_columns(X_train_p, drop_original=True)

        # X_test_p = transform_date_columns(X_test_p, drop_original=True)



        # Forcer dtype 'category' pour colonnes catégorielles détectées

        for col in (categorical_features or []):

            if col in X_train_p.columns:

                try:

                    X_train_p[col] = X_train_p[col].astype('category')

                except Exception:

                    pass

            if col in X_test_p.columns:

                try:

                    X_test_p[col] = X_test_p[col].astype('category')

                except Exception:

                    pass



        feature_names = list(X_train_p.columns)

        result = {

            'X_train': X_train_p,

            'X_test': X_test_p,

            'preprocessor': None,

            'feature_names': feature_names,

            'numeric_features': numeric_features,

            'categorical_features': categorical_features

        }



        logger.info("\n✓ Préparation AutoGluon terminée\n")

        return result



    # Créer le preprocessor

    logger.info("\n2️⃣ Création du preprocessor...")

    preprocessor = create_preprocessor(numeric_features, categorical_features)



    # Appliquer sur train set

    logger.info("\n3️⃣ Transformation du training set...")

    X_train_transformed = preprocessor.fit_transform(X_train)

    logger.info(f"  ✓ Shape: {X_train_transformed.shape}")



    # Appliquer sur test set

    logger.info("\n4️⃣ Transformation du test set...")

    X_test_transformed = preprocessor.transform(X_test)

    logger.info(f"  ✓ Shape: {X_test_transformed.shape}")



    # Récupérer les noms des features

    logger.info("\n5️⃣ Récupération des noms de features...")

    feature_names = get_feature_names(preprocessor, numeric_features, categorical_features)

    logger.info(f"  ✓ {len(feature_names)} features au total")



    result = {

        'X_train': X_train_transformed,

        'X_test': X_test_transformed,

        'preprocessor': preprocessor,

        'feature_names': feature_names,

        'numeric_features': numeric_features,

        'categorical_features': categorical_features

    }



    logger.info("\n✓ Préparation des données terminée\n")

    return result





def transform_new_data(X_new, preprocessor, drop_columns=None, strip_columns=True):

    """

    Transforme de nouvelles données avec un preprocessor déjà configuré.



    Args:

        X_new: Nouvelles données à transformer

        preprocessor: ColumnTransformer déjà fitted

        drop_columns: liste de colonnes à supprimer avant transformation

        strip_columns: bool, si True nettoie les noms de colonnes



    Returns:

        array or DataFrame: Données transformées

    """

    X_new_p = X_new.copy()



    if strip_columns:

        X_new_p.columns = X_new_p.columns.str.strip()



    if drop_columns:

        X_new_p = X_new_p.drop(columns=[col for col in drop_columns if col in X_new_p.columns], errors='ignore')



    X_new_p = transform_date_columns(X_new_p, drop_original=True)



    if preprocessor is None:

        logger.info("✓ Aucun preprocessor fourni — mode AutoGluon, retourne DataFrame après transformations légères")

        return X_new_p



    X_new_transformed = preprocessor.transform(X_new_p)

    logger.info(f"✓ Nouvelles données transformées: {X_new_transformed.shape}")

    return X_new_transformed





def split_data(data, test_size=0.2, random_state=42, target_column=None):

    """

    Divise les données en ensemble d'entraînement et de test

    Nettoie aussi les données (NaN, types)

    """

    from sklearn.model_selection import train_test_split



    if data is None or data.empty:

        raise ValueError("Les données sont vides ou None")



    # Nettoyer les données

    data_clean = data.dropna()  # Supprimer les NaN

    if data_clean.empty:

        raise ValueError("Toutes les données contiennent des NaN")



    logger.info(f"Données après nettoyage: {data_clean.shape}")

    logger.info("Aperçu des premières lignes de data_clean:")

    logger.info(data_clean.head(2))



    # Priorité : paramètre explicite > config.yaml > fallback

    target_col = None

    if target_column is not None and target_column in data_clean.columns:

        target_col = target_column



    logger.info(f"Colonne cible utilisée (paramètre): {target_col}")



    if target_col:

        y = data_clean[target_col]

        X = data_clean.drop(columns=[target_col])

    else:

        # Fallback: dernière colonne

        X = data_clean.iloc[:, :-1]

        y = data_clean.iloc[:, -1]

        logger.info(f"Colonne cible utilisée (fallback): {y.name}")



    logger.info(f"Features shape: {X.shape}, Target shape: {y.shape}")

    logger.info("Aperçu des premières lignes de X:")

    logger.info(X.head(2))

    logger.info("Aperçu des premières lignes de y:")

    logger.info(y.head(2))



    y = y.astype(str).str.strip()

    y = pd.to_numeric(y, errors='coerce')



    mask = y.notna()

    X = X[mask]

    y = y[mask]



    # Vérifier que X et y ne sont pas vides

    if X.empty or y.empty:

        raise ValueError(f"X ou y vide après split: X.shape={X.shape}, y.shape={y.shape}")



    # Convertir y en numérique si possible

    try:

        y = pd.to_numeric(y, errors='coerce').dropna()

        # Re-aligner X et y après conversion

        X = X.loc[y.index]

    except Exception as e:

        logger.info(f"Attention: Conversion numérique de y échouée: {e}")



    # Ne pas convertir X en float32 ici - laisser le preprocessing s'en occuper

    # (surtout pour AutoGluon qui gère les catégories nativement)



    if X.empty:

        raise ValueError("X est vide après conversion")



    X_train, X_test, y_train, y_test = train_test_split(

        X, y, 

        test_size=test_size,

        random_state=random_state,

        stratify=None  # Pas de stratification si y est continu

    )



    logger.info(f"Ensemble d'entraînement: {X_train.shape}")

    logger.info(f"Ensemble de test: {X_test.shape}")



    return X_train, X_test, y_train, y_test

