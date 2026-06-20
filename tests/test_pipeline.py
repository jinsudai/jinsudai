import sys
import os
os.environ['PYTHONPATH'] = 'src'
sys.path.insert(0, 'src')

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(".env"), override=True)
load_dotenv(find_dotenv(".env.secrets"), override=True)

from ml.pipelines.training_pipeline import MLPipeline

file_path = "data/templates/training_template.csv"

print("\n>>> Initialisation du pipeline...\n")
pipeline = MLPipeline(config_name="consumption")
pipeline2 = pipeline

print("\n1. Chargement des données...")
pipeline2.step_1_load_data(file_path)

print("\n2. Validation des données...")
pipeline2.step_2_validate_data()

print("\n3a. Transformation des données...")
pipeline2.step_3_transform_data()

print("\n3b. Préparation des données...")
pipeline2.step_3_prepare_data()
