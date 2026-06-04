## Exploration

`exploration.ipynb` permet de construire un modèle à partir de `training_pipeline.py` et d'une config domaine :

- Consommation : `src/ml/consumption/configs/config.yaml`
- Production solaire : `src/ml/solar_production/configs/config.yaml`

Données d'exemple : `data/template/training_template.csv` (format PRM). Pour un jeu réel, placer un CSV sous `data/raw/`.

### Étapes

- Ouvrir un terminal à la racine du projet
- `poetry install` puis `poetry run jupyter lab`
- Ouvrir `notebooks/exploration.ipynb`
