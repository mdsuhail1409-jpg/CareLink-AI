# 🏥 CareLink AI – Preventive Healthcare Monitoring App

## 📌 Project Overview
CareLink AI is a 24/7 real-time healthcare monitoring system designed to track hospital or home patients' vital signs. It utilizes a **Machine Learning model** to predict health risks (Normal vs. High Risk) based on live data and provides a **simulation engine** to generate realistic patient vitals (Heart Rate, Temperature, SpO₂).

## 🚀 Key Features
- **Role-Based Access**: Separate views for Doctors and Healthcare Staff.
- **Real-Time Monitoring**: Live dashboard updating every 2 seconds.
- **AI Risk Prediction**: Random Forest model to detect anomalies in vitals.
- **Patient Simulator**: Generates realistic data for 10 independent patients, including vitals drift and occasional spikes.
- **Responsive Design**: Premium, dark-mode medical UI.

## 📂 Project Structure
```
CareLink AI/
│
├── backend/
│   ├── app.py              # Flask API Server
│   ├── simulator.py        # Patient Vitals Simulator Engine
│   ├── predict.py          # ML Prediction Logic
│   ├── train_model.py      # Script to train/retrain the model
│   └── model.pkl           # Trained ML Model (Saved Artifact)
│
├── frontend/
│   ├── index.html          # Landing & Role Selection
│   ├── login.html          # Authentication Page
│   ├── patients.html       # Main Patient List
│   ├── dashboard.html      # Individual Patient Monitor
│   ├── style.css           # Custom Styling
│   ├── script.js           # Frontend Logic & API Fetching
│   └── chart.js            # Charting Library (Local)
│
├── requirements.txt        # Python Dependencies
└── run_app.bat             # One-click Launcher
```

## 🛠️ Technology Stack
- **Backend**: Python, Flask, Scikit-Learn, Pandas, NumPy
- **Frontend**: HTML5, CSS3 (Custom), JavaScript (ES6+), Chart.js
- **Machine Learning**: Random Forest Classifier

## ⚙️ How to Run
### Option 1: One-Click (Windows)
Double-click the `run_app.bat` file in the project folder.

### Option 2: Manual Setup
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Train Model** (First time only, or to reset):
   ```bash
   python backend/train_model.py
   ```
3. **Start Backend**:
   ```bash
   python backend/app.py
   ```
4. **Open Frontend**:
   Open `frontend/index.html` in your web browser.

## 🧪 Testing & Validation
- **Normal Case**: Vitals stable (HR 60-100, Temp 36-37, SpO2 > 95) → Risk: NORMAL
- **High Risk Case**: Simulator triggers spike (HR > 100 or Low SpO2) → Risk: HIGH RISK (Red Alert)

## 🔮 Future Scope
- Integration with real IoT sensors.
- Historical data storage (Database integration).
- SMS/Email alerts for doctors.
