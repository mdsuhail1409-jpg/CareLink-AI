import joblib
import numpy as np
import os

# Fallback class in case sklearn fails
class RuleBasedModel:
    def predict(self, X):
        predictions = []
        # X is expected to be a list of lists or 2D array: [[hr, temp, spo2], ...]
        for row in X:
            # handle both DataFrame rows and numpy arrays/lists
            if hasattr(row, 'iloc'):
                hr, temp, spo2 = row
            else:
                hr, temp, spo2 = row
                
            # Logic: High Risk if HR > 100 OR Temp > 38.0 OR SpO2 < 90
            if hr > 100 or temp > 38.0 or spo2 < 90:
                predictions.append(1)
            else:
                predictions.append(0)
        return predictions
    
    def score(self, X, y):
        preds = self.predict(X)
        correct = sum(p == t for p, t in zip(preds, y))
        return correct / len(y)

try:
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    
    print("Scikit-learn found. Training Random Forest...")
    
    # 1. Generate Synthetic Data
    n_samples = 1000
    np.random.seed(42)
    heart_rate = np.random.randint(60, 130, n_samples)
    temperature = np.random.uniform(36.0, 40.5, n_samples)
    spo2 = np.random.randint(70, 100, n_samples)

    risk = []
    for h, t, s in zip(heart_rate, temperature, spo2):
        if h > 100 or t > 38.0 or s < 90:
            risk.append(1)
        else:
            risk.append(0)

    data = pd.DataFrame({
        'heart_rate': heart_rate,
        'temperature': temperature,
        'spo2': spo2,
        'risk': risk
    })

    X = data[['heart_rate', 'temperature', 'spo2']]
    y = data['risk']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    print(f"Model Accuracy: {model.score(X_test, y_test) * 100:.2f}%")

except ImportError as e:
    print(f"ImportError ({e}). Using Rule-Based Fallback Model.")
    model = RuleBasedModel()
except Exception as e:
    print(f"An error occurred ({e}). Using Rule-Based Fallback Model.")
    model = RuleBasedModel()

# 3. Save Model
# 3. Save Model
# Use path relative to this script to ensure correct location regardless of CWD
current_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(current_dir, 'model.pkl')

joblib.dump(model, output_path)
print(f"Model saved to {output_path}")
