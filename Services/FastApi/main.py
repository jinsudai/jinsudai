"""
FastAPI Service - Consumption Prediction API

Endpoints:
- /predict: Predict energy consumption
- /health: Health check for monitoring
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# Add src to path to import ml modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ml.utils.models.models_inference import InferenceModel
from ml.config import get_mlflow_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Consumption Prediction API",
    description="API for predicting energy consumption using MLflow models",
    version="1.0.0"
)

# Configuration
ENV = os.getenv("ENV", "dev")

# Global inference model variable (lazy loaded)
_inference_model = None


class PredictionRequest(BaseModel):
    """Request model for prediction endpoint."""
    
    Horodate: str = Field(..., description="Timestamp in ISO format (e.g., '2024-01-01T00:00:00')")
    temperature_2m_mean: float = Field(..., description="Mean temperature in Celsius")
    relative_humidity_mean: float = Field(..., description="Mean relative humidity percentage")
    precipitation_sum: float = Field(default=0.0, description="Total precipitation in mm")
    is_vacances: int = Field(default=0, description="1 if vacation period, 0 otherwise")
    jour_de_la_semaine: str = Field(default="", description="Day of the week in French")
    jour_ferie: int = Field(default=0, description="1 if public holiday, 0 otherwise")


class PredictionResponse(BaseModel):
    """Response model for prediction endpoint."""
    
    prediction: float = Field(..., description="Predicted consumption value in kWh")
    timestamp: str = Field(..., description="Prediction timestamp")
    model_version: str = Field(..., description="MLflow model version used")


class HealthResponse(BaseModel):
    """Response model for health endpoint."""
    
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    model_loaded: bool = Field(..., description="Whether the model is loaded")
    model_version: Optional[str] = Field(None, description="MLflow model version")
    mlflow_tracking_uri: str = Field(..., description="MLflow tracking URI")


def get_inference_model():
    """Get the inference model, loading it if necessary."""
    global _inference_model
    if _inference_model is None:
        try:
            # Get MLflow config from the project config
            mlflow_config = get_mlflow_config()
            
            # Initialize InferenceModel with project config
            _inference_model = InferenceModel(
                mlflow_tracking_uri=mlflow_config.get("tracking_uri"),
                experiment_name=mlflow_config.get("experiment_name")
            )
            
            # Load production model
            model_name = mlflow_config.get("model_name")
            alias_prod = mlflow_config.get("prod_alias", "prod")
            
            success = _inference_model.load_production_model(
                model_name=model_name,
                alias_prod=alias_prod
            )
            
            if not success:
                raise RuntimeError(f"Failed to load model {model_name} from MLflow")
            
            logger.info(f"Model loaded successfully: {model_name} (version {_inference_model.model_version})")
            
        except Exception as e:
            logger.error(f"Failed to load inference model: {e}")
            raise
    
    return _inference_model


@app.on_event("startup")
async def startup_event():
    """Load the model on startup."""
    logger.info("Starting FastAPI service...")
    try:
        get_inference_model()
        logger.info("FastAPI service started successfully")
    except Exception as e:
        logger.warning(f"Model not loaded on startup: {e}. Will load on first request.")


@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns the service status, model loading status, and MLflow configuration.
    """
    global _inference_model
    
    model_version = None
    mlflow_tracking_uri = "unknown"
    
    if _inference_model is not None:
        model_version = _inference_model.model_version
        mlflow_tracking_uri = _inference_model.mlflow_tracking_uri
    else:
        try:
            mlflow_config = get_mlflow_config()
            mlflow_tracking_uri = mlflow_config.get("tracking_uri", "unknown")
        except Exception:
            pass
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        model_loaded=_inference_model is not None,
        model_version=model_version,
        mlflow_tracking_uri=mlflow_tracking_uri
    )


@app.post("/predict", response_model=PredictionResponse, tags=["prediction"])
async def predict(request: PredictionRequest):
    """
    Predict energy consumption.
    
    Args:
        request: PredictionRequest containing the features for prediction
        
    Returns:
        PredictionResponse with the predicted consumption value
    """
    try:
        # Get the inference model
        inference_model = get_inference_model()
        
        # Convert request to DataFrame
        data = {
            "Horodate": [request.Horodate],
            "temperature_2m_mean": [request.temperature_2m_mean],
            "relative_humidity_mean": [request.relative_humidity_mean],
            "precipitation_sum": [request.precipitation_sum],
            "is_vacances": [request.is_vacances],
            "jour de la semaine": [request.jour_de_la_semaine],
            "jour férié": [request.jour_ferie]
        }
        df = pd.DataFrame(data)
        
        # Make prediction using InferenceModel
        predictions, _ = inference_model.predict(df)
        
        if predictions is None:
            raise RuntimeError("Prediction returned None")
        
        # Return prediction
        return PredictionResponse(
            prediction=float(predictions[0]),
            timestamp=datetime.utcnow().isoformat(),
            model_version=inference_model.model_version or "unknown"
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/predict/batch", response_model=List[PredictionResponse], tags=["prediction"])
async def predict_batch(requests: List[PredictionRequest]):
    """
    Batch prediction endpoint for multiple predictions.
    
    Args:
        requests: List of PredictionRequest objects
        
    Returns:
        List of PredictionResponse objects
    """
    try:
        # Get the inference model
        inference_model = get_inference_model()
        
        # Convert requests to DataFrame
        data = []
        for req in requests:
            data.append({
                "Horodate": req.Horodate,
                "temperature_2m_mean": req.temperature_2m_mean,
                "relative_humidity_mean": req.relative_humidity_mean,
                "precipitation_sum": req.precipitation_sum,
                "is_vacances": req.is_vacances,
                "jour de la semaine": req.jour_de_la_semaine,
                "jour férié": req.jour_ferie
            })
        df = pd.DataFrame(data)
        
        # Make predictions using InferenceModel
        predictions, _ = inference_model.predict(df)
        
        if predictions is None:
            raise RuntimeError("Batch prediction returned None")
        
        # Return predictions
        timestamp = datetime.utcnow().isoformat()
        return [
            PredictionResponse(
                prediction=float(pred),
                timestamp=timestamp,
                model_version=inference_model.model_version or "unknown"
            )
            for pred in predictions
        ]
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
