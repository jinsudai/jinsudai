"""
Streamlit Service - 48-Hour Consumption Prediction UI

This service provides a web interface to request energy consumption predictions
for the next 48 hours (or multiple days up to 16 days based on weather API limits).

Features:
- Select number of days for prediction (1-16 days)
- Fetch weather forecast data from Open-Meteo API
- Generate consumption predictions using MLflow model
- Display predictions in interactive charts and tables
- Export predictions to CSV
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Add src to path to import ml modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ml.connectors.weather.weather_api import WeatherAPI
from ml.utils.models.models_inference import InferenceModel
from ml.utils.data.data_prediction import generate_inference_data, add_predictions_to_data
from ml.config import get_mlflow_config, load_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Prédictions Consommation - 48h",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_inference_model():
    """Load the inference model (cached for performance)."""
    try:
        mlflow_config = get_mlflow_config()
        
        inference_model = InferenceModel(
            mlflow_tracking_uri=mlflow_config.get("tracking_uri"),
            experiment_name=mlflow_config.get("experiment_name")
        )
        
        model_name = mlflow_config.get("model_name")
        alias_prod = mlflow_config.get("prod_alias", "prod")
        
        success = inference_model.load_production_model(
            model_name=model_name,
            alias_prod=alias_prod
        )
        
        if not success:
            st.error(f"Failed to load model {model_name} from MLflow")
            return None
        
        logger.info(f"Model loaded successfully: {model_name}")
        return inference_model
        
    except Exception as e:
        logger.error(f"Failed to load inference model: {e}")
        st.error(f"Erreur lors du chargement du modèle: {e}")
        return None


@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_weather_forecast(latitude: float, longitude: float, forecast_days: int):
    """Fetch weather forecast data (cached for 1 hour)."""
    try:
        weather_api = WeatherAPI(
            latitude=latitude,
            longitude=longitude,
            location_name=f"Location ({latitude}, {longitude})"
        )
        
        df_weather = weather_api.fetch_forecast(
            forecast_days=forecast_days,
            hourly=True
        )
        
        # Validate data
        validation = weather_api.validate_data()
        if not validation["is_valid"]:
            st.warning(f"Warnings in weather data: {validation['warnings']}")
        
        return df_weather, validation
        
    except Exception as e:
        logger.error(f"Failed to fetch weather forecast: {e}")
        st.error(f"Erreur lors de la récupération des prévisions météo: {e}")
        return None, None


def generate_predictions(inference_model, n_days: int, n_samples_per_day: int, latitude: float, longitude: float):
    """Generate consumption predictions using weather data."""
    try:
        # Load consumption config to get weather location
        config = load_config("consumption")
        
        # Override weather location with user selection
        config['data']['weather_latitude'] = latitude
        config['data']['weather_longitude'] = longitude
        config['data']['weather_location'] = f"Custom ({latitude}, {longitude})"
        
        # Generate inference data with weather
        df_inference = generate_inference_data(
            n_days=n_days,
            n_samples_per_day=n_samples_per_day,
            config_name="consumption",
            config_path="src/configs/consumption.yaml"
        )
        
        if df_inference is None or df_inference.empty:
            st.error("Failed to generate inference data")
            return None
        
        # Make predictions
        predictions, confidence_scores = inference_model.predict(df_inference)
        
        if predictions is None:
            st.error("Failed to generate predictions")
            return None
        
        # Add predictions to dataframe
        df_predictions = add_predictions_to_data(df_inference, predictions, confidence_scores)
        
        return df_predictions
        
    except Exception as e:
        logger.error(f"Failed to generate predictions: {e}")
        st.error(f"Erreur lors de la génération des prédictions: {e}")
        return None


def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<h1 class="main-header">⚡ Prédictions de Consommation Énergétique</h1>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    
    # Location settings
    st.sidebar.subheader("📍 Localisation")
    latitude = st.sidebar.slider(
        "Latitude",
        min_value=40.0,
        max_value=52.0,
        value=48.8566,  # Paris
        step=0.1,
        help="Latitude de la localisation"
    )
    
    longitude = st.sidebar.slider(
        "Longitude",
        min_value=-5.0,
        max_value=10.0,
        value=2.3522,  # Paris
        step=0.1,
        help="Longitude de la localisation"
    )
    
    # Prediction settings
    st.sidebar.subheader("🔮 Prédictions")
    forecast_days = st.sidebar.slider(
        "Nombre de jours de prévision",
        min_value=1,
        max_value=16,
        value=1,
        step=1,
        help="Nombre de jours pour les prévisions météo (max 16 jours selon API Open-Meteo)"
    )
    
    n_samples_per_day = st.sidebar.slider(
        "Échantillons par jour",
        min_value=24,
        max_value=96,
        value=48,
        step=24,
        help="Nombre d'échantillons par jour (48 = toutes les 30 minutes)"
    )
    
    # Calculate total predictions
    total_predictions = forecast_days * n_samples_per_day
    st.sidebar.info(f"Total prédictions: {total_predictions}")
    
    # Load model
    st.sidebar.subheader("🤖 Modèle ML")
    with st.sidebar:
        with st.spinner("Chargement du modèle..."):
            inference_model = get_inference_model()
    
    if inference_model is None:
        st.error("Impossible de charger le modèle. Vérifiez la configuration MLflow.")
        st.stop()
    
    # Display model info
    model_info = inference_model.get_model_info()
    if model_info:
        st.sidebar.success(f"Modèle: {model_info.get('model_name', 'Unknown')}")
        st.sidebar.info(f"Version: {model_info.get('version', 'Unknown')}")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Prévisions Météo & Prédictions")
        
        # Generate predictions button (combines weather fetch + prediction)
        if st.button("Générer les prédictions de consommation", type="primary", use_container_width=True):
            with st.spinner(f"Génération des prédictions pour {total_predictions} points..."):
                df_predictions = generate_predictions(
                    inference_model=inference_model,
                    n_days=forecast_days,
                    n_samples_per_day=n_samples_per_day,
                    latitude=latitude,
                    longitude=longitude
                )
                
                if df_predictions is not None:
                    st.session_state['df_predictions'] = df_predictions
                    st.success(f"✅ Prédictions générées: {len(df_predictions)} enregistrements")
                else:
                    st.error("Échec de la génération des prédictions")
    
    with col2:
        st.subheader("ℹ️ Informations")
        st.info(f"""
        **Localisation**: {latitude:.2f}, {longitude:.2f}
        
        **Période**: {forecast_days} jour(s)
        
        **Échantillons**: {n_samples_per_day}/jour
        
        **API**: Open-Meteo (max 16 jours)
        """)
    
    # Display predictions if available
    if 'df_predictions' in st.session_state:
        df_predictions = st.session_state['df_predictions']
        
        # Weather statistics from predictions
        st.subheader("🌡️ Statistiques Météo")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_temp = df_predictions['temperature_2m_mean'].mean()
            st.metric("Température Moyenne", f"{avg_temp:.1f}°C")
        
        with col2:
            avg_humidity = df_predictions['relative_humidity_mean'].mean()
            st.metric("Humidité Moyenne", f"{avg_humidity:.1f}%")
        
        with col3:
            total_precip = df_predictions['precipitation_sum'].sum()
            st.metric("Précipitations Totales", f"{total_precip:.1f}mm")
        
        # Weather chart
        st.subheader("📈 Évolution Météo")
        fig_weather = go.Figure()
        
        fig_weather.add_trace(go.Scatter(
            x=df_predictions['Horodate'],
            y=df_predictions['temperature_2m_mean'],
            mode='lines',
            name='Température (°C)',
            line=dict(color='red')
        ))
        
        fig_weather.add_trace(go.Scatter(
            x=df_predictions['Horodate'],
            y=df_predictions['relative_humidity_mean'],
            mode='lines',
            name='Humidité (%)',
            line=dict(color='blue'),
            yaxis='y2'
        ))
        
        fig_weather.update_layout(
            title='Prévisions Météo',
            xaxis_title='Date/Heure',
            yaxis_title='Température (°C)',
            yaxis2=dict(
                title='Humidité (%)',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_weather, use_container_width=True)
        
        # Prediction statistics
        st.subheader("📊 Statistiques des Prédictions")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_consumption = df_predictions['prediction'].sum()
            st.metric("Consommation Totale", f"{total_consumption:.2f} kWh")
        
        with col2:
            avg_consumption = df_predictions['prediction'].mean()
            st.metric("Consommation Moyenne", f"{avg_consumption:.2f} kWh")
        
        with col3:
            max_consumption = df_predictions['prediction'].max()
            st.metric("Consommation Max", f"{max_consumption:.2f} kWh")
        
        with col4:
            min_consumption = df_predictions['prediction'].min()
            st.metric("Consommation Min", f"{min_consumption:.2f} kWh")
        
        # Prediction chart
        st.subheader("📈 Courbe des Prédictions")
        fig_pred = px.line(
            df_predictions,
            x='Horodate',
            y='prediction',
            title='Prédictions de Consommation Énergétique',
            labels={'prediction': 'Consommation (kWh)', 'Horodate': 'Date/Heure'}
        )
        
        fig_pred.update_layout(
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig_pred, use_container_width=True)
        
        # Confidence chart if available
        if 'confidence' in df_predictions.columns:
            st.subheader("🎯 Scores de Confiance")
            fig_conf = px.line(
                df_predictions,
                x='Horodate',
                y='confidence',
                title='Scores de Confiance du Modèle',
                labels={'confidence': 'Confiance', 'Horodate': 'Date/Heure'}
            )
            fig_conf.update_layout(hovermode='x unified', height=300)
            st.plotly_chart(fig_conf, use_container_width=True)
        
        # Data table
        st.subheader("📋 Données de Prédiction")
        
        # Add date filter
        df_predictions_display = df_predictions.copy()
        df_predictions_display['Date'] = pd.to_datetime(df_predictions_display['Horodate']).dt.date
        
        unique_dates = df_predictions_display['Date'].unique()
        selected_date = st.selectbox(
            "Filtrer par date",
            options=["Toutes les dates"] + list(unique_dates),
            index=0
        )
        
        if selected_date != "Toutes les dates":
            df_predictions_display = df_predictions_display[
                df_predictions_display['Date'] == selected_date
            ]
        
        # Select columns to display
        display_columns = ['Horodate', 'prediction']
        if 'confidence' in df_predictions_display.columns:
            display_columns.append('confidence')
        display_columns.extend(['temperature_2m_mean', 'relative_humidity_mean'])
        
        st.dataframe(
            df_predictions_display[display_columns],
            use_container_width=True,
            height=400
        )
        
        # Export button
        st.subheader("💾 Exporter les Données")
        col1, col2 = st.columns(2)
        
        with col1:
            csv = df_predictions.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Télécharger en CSV",
                data=csv,
                file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Export to parquet
            parquet_buffer = df_predictions.to_parquet(index=False)
            st.download_button(
                label="Télécharger en Parquet",
                data=parquet_buffer,
                file_name=f"predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet",
                mime="application/octet-stream",
                use_container_width=True
            )


if __name__ == "__main__":
    main()
