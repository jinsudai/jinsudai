"""
Tests unitaires simples pour la classe MonitoringPipeline.

Tests couverts :
- Initialisation de la classe
- Méthodes de chargement de données
- Détection de drift
- Génération de rapports

Utilisation :
    pytest tests/test_monitoring_pipeline.py -v
"""
import sys
sys.path.insert(0, 'src')

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import pandas as pd
import numpy as np

from ml.pipelines.monitoring import MonitoringPipeline


class TestMonitoringPipeline(unittest.TestCase):
    """Tests simples pour la classe MonitoringPipeline."""

    def setUp(self):
        """Configuration initiale pour chaque test."""
        # Mock la config pour éviter les dépendances externes
        with patch('ml.pipelines.monitoring.load_config') as mock_config, \
             patch('ml.pipelines.monitoring.get_database_uri') as mock_db_uri:
            
            mock_config.return_value = {
                'drift_detection': {
                    'reference_data_path': 'data/test_reference.parquet'
                },
                'data': {
                    'target_column': 'Valeur',
                    'feature_columns': ['feature1', 'feature2']
                },
                'email': {'enabled': False},
                'mlflow': {'model_name': 'test_model'}
            }
            mock_db_uri.return_value = 'postgresql://test'
            
            self.pipeline = MonitoringPipeline(config_name="consumption")

    def test_initialization(self):
        """Test l'initialisation de la classe."""
        self.assertIsNotNone(self.pipeline.config)
        self.assertEqual(self.pipeline.db_uri, 'postgresql://test')
        self.assertIsNone(self.pipeline.reference_data)
        self.assertIsNone(self.pipeline.current_data)
        self.assertIsNone(self.pipeline.drift_results)

    def test_get_drift_results_none(self):
        """Test get_drift_results quand aucun drift n'a été détecté."""
        result = self.pipeline.get_drift_results()
        self.assertIsNone(result)

    def test_is_drift_detected_none(self):
        """Test is_drift_detected quand aucun résultat n'est disponible."""
        result = self.pipeline.is_drift_detected()
        self.assertFalse(result)

    def test_is_drift_detected_with_results(self):
        """Test is_drift_detected avec des résultats de drift."""
        self.pipeline.drift_results = {'overall_drift_detected': True}
        result = self.pipeline.is_drift_detected()
        self.assertTrue(result)

    def test_is_drift_detected_false_with_results(self):
        """Test is_drift_detected quand drift n'est pas détecté."""
        self.pipeline.drift_results = {'overall_drift_detected': False}
        result = self.pipeline.is_drift_detected()
        self.assertFalse(result)

    @patch('ml.pipelines.monitoring.load_reference_data')
    def test_step_1_load_reference_data_success(self, mock_load):
        """Test le chargement des données de référence avec succès."""
        mock_load.return_value = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6],
            'Valeur': [10, 20, 30]
        })

        with patch('pathlib.Path.exists', return_value=True):
            result = self.pipeline.step_1_load_reference_data(
                reference_path='data/test.parquet',
                download_from_s3_if_missing=False
            )

        self.assertTrue(result)
        self.assertIsNotNone(self.pipeline.reference_data)
        self.assertEqual(len(self.pipeline.reference_data), 3)

    @patch('ml.pipelines.monitoring.load_reference_data')
    def test_step_1_load_reference_data_failure(self, mock_load):
        """Test le chargement des données de référence en échec."""
        mock_load.return_value = None

        with patch('pathlib.Path.exists', return_value=True):
            result = self.pipeline.step_1_load_reference_data(
                reference_path='data/test.parquet',
                download_from_s3_if_missing=False
            )

        self.assertFalse(result)

    @patch('ml.pipelines.monitoring.load_reference_data')
    def test_step_1_load_reference_data_no_path(self, mock_load):
        """Test le chargement sans chemin fourni."""
        result = self.pipeline.step_1_load_reference_data(
            reference_path=None,
            download_from_s3_if_missing=False
        )

        self.assertFalse(result)

    @patch('pandas.read_parquet')
    def test_step_2_load_current_data_success(self, mock_read):
        """Test le chargement des données courantes avec succès."""
        mock_read.return_value = pd.DataFrame({
            'feature1': [1, 2],
            'feature2': [4, 5],
            'Valeur': [10, 20]
        })

        result = self.pipeline.step_2_load_current_data(
            current_data_path='data/current.parquet',
            limit=1000
        )

        self.assertTrue(result)
        self.assertIsNotNone(self.pipeline.current_data)

    @patch('pandas.read_parquet')
    def test_step_2_load_current_data_failure(self, mock_read):
        """Test le chargement des données courantes en échec."""
        mock_read.side_effect = Exception("File not found")

        result = self.pipeline.step_2_load_current_data(
            current_data_path='data/current.parquet',
            limit=1000
        )

        self.assertFalse(result)

    @patch('ml.pipelines.monitoring.run_drift_detection')
    @patch('ml.pipelines.monitoring.MonitoringPipeline._generate_reference_predictions')
    def test_step_3_detect_drift_success(self, mock_gen_pred, mock_detect):
        """Test la détection de drift avec succès."""
        # Préparer les données avec assez d'échantillons (>= 96)
        self.pipeline.reference_data = pd.DataFrame({
            'feature1': [1] * 100,
            'feature2': [4] * 100,
            'Valeur': [10] * 100
        })
        self.pipeline.current_data = pd.DataFrame({
            'feature1': [1] * 100,
            'feature2': [4] * 100,
            'Valeur': [10] * 100
        })

        mock_gen_pred.return_value = None
        mock_detect.return_value = {
            'overall_drift_detected': False,
            'data_drift': {'drift_detected': False},
            'concept_drift': {'drift_detected': False}
        }

        result = self.pipeline.step_3_detect_drift()

        self.assertTrue(result)
        self.assertIsNotNone(self.pipeline.drift_results)
        self.assertFalse(self.pipeline.drift_results['overall_drift_detected'])

    @patch('ml.pipelines.monitoring.run_drift_detection')
    def test_step_3_detect_drift_failure(self, mock_detect):
        """Test la détection de drift en échec."""
        self.pipeline.reference_data = None
        self.pipeline.current_data = None

        result = self.pipeline.step_3_detect_drift()

        self.assertFalse(result)

    @patch('ml.pipelines.monitoring.generate_evidently_report')
    def test_step_4_generate_report_success(self, mock_generate):
        """Test la génération du rapport avec succès."""
        self.pipeline.reference_data = pd.DataFrame({'feature1': [1, 2]})
        self.pipeline.current_data = pd.DataFrame({'feature1': [1, 2]})
        self.pipeline.drift_results = {'overall_drift_detected': False}

        mock_generate.return_value = (MagicMock(), {'test': 'data'})

        result = self.pipeline.step_4_generate_evidently_report(
            output_path='test_report.html',
            save_to_workspace=False,
            save_to_s3=False
        )

        self.assertTrue(result)

    def test_step_5_store_metrics_no_results(self):
        """Test le stockage des métriques sans résultats."""
        self.pipeline.drift_results = None
        self.pipeline.evidently_report = None

        result = self.pipeline.step_5_store_metrics()

        self.assertFalse(result)

    def test_step_6_send_notifications_no_drift(self):
        """Test les notifications sans drift détecté."""
        self.pipeline.drift_results = {'overall_drift_detected': False}

        result = self.pipeline.step_6_send_notifications()

        self.assertTrue(result)

    def test_step_6_send_notifications_no_results(self):
        """Test les notifications sans résultats."""
        self.pipeline.drift_results = None

        result = self.pipeline.step_6_send_notifications()

        self.assertFalse(result)

    @patch('ml.pipelines.monitoring.MonitoringPipeline.step_1_load_reference_data')
    @patch('ml.pipelines.monitoring.MonitoringPipeline.step_2_load_current_data')
    @patch('ml.pipelines.monitoring.MonitoringPipeline.step_3_detect_drift')
    def test_run_full_pipeline_success(self, mock_step3, mock_step2, mock_step1):
        """Test l'exécution complète du pipeline avec succès."""
        mock_step1.return_value = True
        mock_step2.return_value = True
        mock_step3.return_value = True

        self.pipeline.drift_results = {'overall_drift_detected': False}

        results = self.pipeline.run_full_pipeline(
            generate_report=False,
            store_metrics=False,
            send_notifications=False,
            download_from_s3=False
        )

        self.assertTrue(results['success'])
        self.assertIn('load_reference_data', results['steps_completed'])
        self.assertIn('load_current_data', results['steps_completed'])
        self.assertIn('detect_drift', results['steps_completed'])

    @patch('ml.pipelines.monitoring.MonitoringPipeline.step_1_load_reference_data')
    def test_run_full_pipeline_step1_failure(self, mock_step1):
        """Test le pipeline avec échec à l'étape 1."""
        mock_step1.return_value = False

        results = self.pipeline.run_full_pipeline(
            generate_report=False,
            store_metrics=False,
            send_notifications=False,
            download_from_s3=False
        )

        self.assertFalse(results['success'])
        self.assertIn('Échec du chargement des données de référence', results['error'])


class TestMonitoringPipelineHelpers(unittest.TestCase):
    """Tests pour les méthodes utilitaires de MonitoringPipeline."""

    @patch('ml.pipelines.monitoring.load_config')
    @patch('ml.pipelines.monitoring.get_database_uri')
    def test_get_model_info_from_api_success(self, mock_db_uri, mock_config):
        """Test la récupération des infos du modèle depuis l'API."""
        mock_config.return_value = {
            'fastapi': {'url': 'http://localhost:8000'},
            's3': {},
            'evidently': {},
            'email': {}
        }
        mock_db_uri.return_value = 'postgresql://test'

        pipeline = MonitoringPipeline(config_name="consumption")

        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'model_name': 'test_model',
                'model_version': 'v1.0'
            }
            mock_get.return_value = mock_response

            result = pipeline._get_model_info_from_api()

            self.assertEqual(result['model_name'], 'test_model')
            self.assertEqual(result['model_version'], 'v1.0')

    @patch('ml.pipelines.monitoring.load_config')
    @patch('ml.pipelines.monitoring.get_database_uri')
    def test_get_model_info_from_api_no_url(self, mock_db_uri, mock_config):
        """Test la récupération des infos sans URL configurée."""
        mock_config.return_value = {
            'fastapi': {},
            's3': {},
            'evidently': {},
            'email': {}
        }
        mock_db_uri.return_value = 'postgresql://test'

        pipeline = MonitoringPipeline(config_name="consumption")

        result = pipeline._get_model_info_from_api()

        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
