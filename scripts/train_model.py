"""
Script to generate a pre-trained Isolation Forest model for fraud detection.
Run this script to create the model.joblib file.
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path


def generate_training_data(n_samples: int = 10000, fraud_ratio: float = 0.05):
    """Generate synthetic training data for the fraud detector."""
    np.random.seed(42)
    
    n_fraud = int(n_samples * fraud_ratio)
    n_normal = n_samples - n_fraud
    
    # Normal transactions
    normal_data = np.column_stack([
        np.random.uniform(0.01, 0.3, n_normal),      # amount_normalized (small-medium)
        np.random.uniform(0.25, 0.85, n_normal),      # hour_normalized (business hours)
        np.random.uniform(0, 1, n_normal),            # day_normalized
        np.random.choice([0, 1], n_normal, p=[0.7, 0.3]),  # is_weekend
        np.random.uniform(0, 0.8, n_normal),          # merchant_category_encoded
        np.random.uniform(0, 0.3, n_normal),          # velocity_normalized (low)
        np.random.uniform(0, 0.3, n_normal),          # amount_deviation (low)
        np.random.uniform(0, 0.3, n_normal),          # location_risk (low)
    ])
    
    # Fraudulent transactions (anomalies)
    fraud_data = np.column_stack([
        np.random.uniform(0.4, 1.0, n_fraud),         # amount_normalized (high)
        np.random.uniform(0, 0.25, n_fraud),          # hour_normalized (night hours)
        np.random.uniform(0, 1, n_fraud),             # day_normalized
        np.random.choice([0, 1], n_fraud, p=[0.5, 0.5]),  # is_weekend
        np.random.uniform(0.3, 1.0, n_fraud),         # merchant_category_encoded
        np.random.uniform(0.5, 1.0, n_fraud),         # velocity_normalized (high)
        np.random.uniform(0.5, 1.0, n_fraud),         # amount_deviation (high)
        np.random.uniform(0.5, 1.0, n_fraud),         # location_risk (high)
    ])
    
    # Combine data
    X = np.vstack([normal_data, fraud_data])
    y = np.hstack([np.zeros(n_normal), np.ones(n_fraud)])
    
    # Shuffle
    indices = np.random.permutation(len(X))
    X = X[indices]
    y = y[indices]
    
    return X, y


def train_model():
    """Train and save the fraud detection model."""
    print("Generating training data...")
    X, y = generate_training_data(n_samples=50000)
    
    print("Fitting scaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print("Training Isolation Forest model...")
    model = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        max_samples='auto',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_scaled)
    
    # Create models directory
    models_dir = Path(__file__).parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    
    # Save model and scaler together
    model_path = models_dir / "fraud_model.joblib"
    
    print(f"Saving model to {model_path}...")
    joblib.dump({
        'model': model,
        'scaler': scaler,
        'feature_names': [
            'amount_normalized',
            'hour_normalized',
            'day_normalized',
            'is_weekend',
            'merchant_category_encoded',
            'velocity_normalized',
            'amount_deviation',
            'location_risk'
        ]
    }, model_path)
    
    print("Model training complete!")
    
    # Test prediction
    test_normal = np.array([[0.1, 0.5, 0.3, 0, 0.2, 0.1, 0.1, 0.1]])
    test_fraud = np.array([[0.9, 0.1, 0.5, 1, 0.8, 0.9, 0.8, 0.9]])
    
    test_normal_scaled = scaler.transform(test_normal)
    test_fraud_scaled = scaler.transform(test_fraud)
    
    print(f"\nTest predictions:")
    print(f"Normal transaction score: {model.decision_function(test_normal_scaled)[0]:.4f}")
    print(f"Fraud transaction score: {model.decision_function(test_fraud_scaled)[0]:.4f}")
    
    return model_path


if __name__ == "__main__":
    train_model()
