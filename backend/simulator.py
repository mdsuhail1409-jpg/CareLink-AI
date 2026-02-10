import random
import time
import threading

class Patient:
    def __init__(self, patient_id, name):
        self.id = patient_id
        self.name = name
        # Baseline vitals
        self.baseline_hr = random.randint(65, 85)
        self.baseline_temp = random.uniform(36.5, 37.2)
        self.baseline_spo2 = random.randint(96, 99)
        
        # Current vitals
        self.heart_rate = self.baseline_hr
        self.temperature = self.baseline_temp
        self.spo2 = self.baseline_spo2
        
        # Trend control
        self.trend = "STABLE" # Options: STABLE, DETERIORATING, RECOVERING
        self.trend_duration = 0
        
    def update(self):
        # Base drift
        hr_drift = random.choice([-1, 0, 1])
        temp_drift = random.choice([-0.1, 0, 0.1])
        spo2_drift = random.choice([-1, 0, 1])

        # Apply Trend Bias
        if self.trend == "DETERIORATING":
            # HR goes UP, SpO2 goes DOWN, Temp erratic
            hr_drift += random.choice([0, 1, 2])
            spo2_drift += random.choice([0, -1, -2])
            temp_drift += random.choice([-0.1, 0.1, 0.2])
        elif self.trend == "RECOVERING":
            # Move towards baseline
            if self.heart_rate > self.baseline_hr: hr_drift = -1
            elif self.heart_rate < self.baseline_hr: hr_drift = 1
            
            if self.spo2 < self.baseline_spo2: spo2_drift = 1
            elif self.spo2 > self.baseline_spo2: spo2_drift = -1
            
            if self.temperature > self.baseline_temp: temp_drift = -0.1
            elif self.temperature < self.baseline_temp: temp_drift = 0.1
        
        self.heart_rate += hr_drift
        self.temperature += temp_drift
        self.spo2 += spo2_drift
        
        # Bound checks and ensuring realism
        self.heart_rate = max(50, min(160, self.heart_rate))
        self.temperature = max(35.0, min(42.0, self.temperature))
        self.spo2 = max(80, min(100, self.spo2))
        
        # Occasional spike logic (simulating deterioration) - only if STABLE
        if self.trend == "STABLE" and random.random() < 0.05: 
            self.heart_rate += random.randint(5, 15)
        
        # Occasional recovery - only if STABLE
        if self.trend == "STABLE" and random.random() < 0.05:
            self.heart_rate = int((self.heart_rate + self.baseline_hr) / 2)

    def predict_future(self, minutes=30):
        """Simulate future state without affecting current state."""
        # Create a temporary clone
        sim_hr = self.heart_rate
        sim_temp = self.temperature
        sim_spo2 = self.spo2
        
        # Simulate steps (assuming 2s per update step, so 30 steps/min)
        steps = int(minutes * 60 / 2)
        
        for _ in range(steps):
             # Base drift
            hr_drift = random.choice([-1, 0, 1])
            temp_drift = random.choice([-0.1, 0, 0.1])
            spo2_drift = random.choice([-1, 0, 1])

            # Apply Trend Bias (same logic as update)
            if self.trend == "DETERIORATING":
                hr_drift += random.choice([0, 0.5, 1]) # Slightly damped for long predictions
                spo2_drift += random.choice([0, -0.5, -1])
            elif self.trend == "RECOVERING":
                if sim_hr > self.baseline_hr: hr_drift = -1
                elif sim_hr < self.baseline_hr: hr_drift = 1
                if sim_spo2 < self.baseline_spo2: spo2_drift = 1
                elif sim_spo2 > self.baseline_spo2: spo2_drift = -1

            sim_hr += hr_drift
            sim_temp += temp_drift
            sim_spo2 += spo2_drift
            
            # Bounds
            sim_hr = max(50, min(160, sim_hr))
            sim_temp = max(35.0, min(42.0, sim_temp))
            sim_spo2 = max(80, min(100, sim_spo2))
            
        return {
            "heart_rate": int(sim_hr),
            "temperature": round(sim_temp, 1),
            "spo2": int(sim_spo2)
        }

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "heart_rate": int(self.heart_rate),
            "temperature": round(self.temperature, 1),
            "spo2": int(self.spo2),
            "risk": self.risk,
            "trend": self.trend
        }

from models import db, Patient as PatientModel, VitalsLog
from alerts import AlertManager
from predict import predict_risk

class Simulator:
    def __init__(self, app):
        self.app = app
        self.alert_manager = AlertManager()
        self.running = False
        self.thread = None
        
        # Initialize Patients in DB if empty
        with self.app.app_context():
            if not PatientModel.query.first():
                names = [
                    "John Doe", "Jane Smith", "Alice Johnson", "Bob Brown", 
                    "Charlie Davis", "Eve Wilson", "Frank Miller", "Grace Lee", 
                    "Henry Taylor", "Ivy Clark"
                ]
                for i, name in enumerate(names):
                    p = PatientModel(id=i+1, name=name, age=random.randint(25, 80), gender=random.choice(['M', 'F']))
                    db.session.add(p)
                db.session.commit()
                print("Initialized Patients in DB")

        # Load patients into memory for simulation
        self.patients = []
        with self.app.app_context():
            db_patients = PatientModel.query.all()
            for p in db_patients:
                self.patients.append(Patient(p.id, p.name))

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        step_count = 0
        while self.running:
            with self.app.app_context():
                for patient in self.patients:
                    patient.update()
                    
                    # Calculate Risk
                    current_risk = predict_risk(patient.heart_rate, patient.temperature, patient.spo2)
                    patient.risk = current_risk
                    
                    # CHECK FOR ALERTS (Every update = 2 seconds)
                    self.alert_manager.check_conditions(patient)
                    
                    # Save to DB every 5 steps (10 seconds)
                    if step_count % 5 == 0:
                        log = VitalsLog(
                            patient_id=patient.id,
                            heart_rate=patient.heart_rate,
                            temperature=patient.temperature,
                            spo2=patient.spo2,
                            risk=current_risk
                        )
                        db.session.add(log)
                        
                        # Legacy alert check removed in favor of check_conditions logic
                            
                if step_count % 5 == 0:
                    try:
                        db.session.commit()
                    except Exception as e:
                        print(f"Error saving logs: {e}")
                        db.session.rollback()
                        
            step_count += 1
            time.sleep(2) # Update every 2 seconds

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def get_patient(self, patient_id):
        for p in self.patients:
            if p.id == patient_id:
                return p
        return None

    def get_all_patients(self):
        return self.patients
