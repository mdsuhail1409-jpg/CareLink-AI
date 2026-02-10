import joblib
import numpy as np
import os

# Load the model
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model.pkl')
try:
    model = joblib.load(MODEL_PATH)
except FileNotFoundError:
    print(f"Error: Model not found at {MODEL_PATH}. Please run train_model.py first.")
    model = None

import pandas as pd

def predict_risk(heart_rate, temperature, spo2):
    """
    Predicts health risk based on vitals.
    Returns: 0 (Normal) or 1 (High Risk)
    """
    if model is None:
        return -1 # Error code
    
    # Use DataFrame with feature names to match training data and avoid warnings
    features = pd.DataFrame([[heart_rate, temperature, spo2]], 
                          columns=['heart_rate', 'temperature', 'spo2'])
    prediction = model.predict(features)
    return int(prediction[0])

if __name__ == "__main__":
    # Test Prediction
    print("Test Prediction (Normal):", predict_risk(70, 37.0, 98))
    print("Test Prediction (High Risk):", predict_risk(110, 39.0, 88))
