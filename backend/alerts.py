import logging
from datetime import datetime, timedelta
from models import db, Alert, SOSAlert

# Mock credentials - in production these would be env vars
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "alerts@carelink.ai"

class AlertManager:
    def __init__(self):
        self.last_alert_time = {} # Map patient_id -> last_alert_timestamp
        self.alert_cooldown = 300 # 5 minutes cooldown between alerts for same patient
        
        # State tracking for duration-based alerts
        # Map patient_id -> { 'condition_name': start_time }
        self.consecutive_states = {} 
        
        # Previous vitals for rate-of-change detection
        # Map patient_id -> { 'timestamp': time, 'hr': val }
        self.previous_vitals = {}

        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger('CareLinkAlerts')

    def check_conditions(self, patient):
        """
        Checks for:
        1. Sustained Hypoxia: SpO2 < 88% for > 60s
        2. Sustained Tachycardia: HR > 120 for > 60s
        3. Rapid Deterioration: HR increase > 20 bpm in 30s
        """
        now = datetime.utcnow()
        pid = patient.id
        
        if pid not in self.consecutive_states:
            self.consecutive_states[pid] = {}
        if pid not in self.previous_vitals:
            self.previous_vitals[pid] = [] # List of tuples (time, hr)

        alerts_triggered = []

        # --- 1. Sustained Hypoxia (SpO2 < 88% for > 60s) ---
        if patient.spo2 < 88:
            if 'hypoxia' not in self.consecutive_states[pid]:
                self.consecutive_states[pid]['hypoxia'] = now
            else:
                duration = (now - self.consecutive_states[pid]['hypoxia']).total_seconds()
                if duration > 60:
                    alerts_triggered.append(("CRITICAL", "sustained_hypoxia", f"SUSTAINED HYPOXIA (SpO2 {patient.spo2}% for {int(duration)}s)"))
        else:
            if 'hypoxia' in self.consecutive_states[pid]:
                del self.consecutive_states[pid]['hypoxia']

        # --- 2. Sustained Tachycardia (HR > 120 for > 60s) ---
        if patient.heart_rate > 120:
            if 'tachycardia' not in self.consecutive_states[pid]:
                self.consecutive_states[pid]['tachycardia'] = now
            else:
                duration = (now - self.consecutive_states[pid]['tachycardia']).total_seconds()
                if duration > 60:
                    alerts_triggered.append(("CRITICAL", "sustained_tachycardia", f"SUSTAINED TACHYCARDIA (HR {patient.heart_rate} bpm for {int(duration)}s)"))
        else:
            if 'tachycardia' in self.consecutive_states[pid]:
                del self.consecutive_states[pid]['tachycardia']

        # --- 3. Rapid Deterioration (HR increase > 20 bpm in 30s) ---
        # Keep last 30 seconds of history
        self.previous_vitals[pid].append((now, patient.heart_rate))
        # Remove old entries
        self.previous_vitals[pid] = [x for x in self.previous_vitals[pid] if (now - x[0]).total_seconds() <= 30]
        
        if len(self.previous_vitals[pid]) > 1:
            oldest_hr = self.previous_vitals[pid][0][1]
            if (patient.heart_rate - oldest_hr) > 20:
                alerts_triggered.append(("CRITICAL", "rapid_deterioration", f"RAPID DETERIORATION (HR +{patient.heart_rate - oldest_hr} bpm in <30s)"))

        # --- Process Alerts ---
        for severity, alert_type, message in set(alerts_triggered): # Use set to avoid duplicates
            if self._can_send_alert(pid): # Global debounce for now, can be per-condition
                self._send_alert(patient, severity, alert_type, message)
                self.last_alert_time[pid] = now

    def _can_send_alert(self, patient_id):
        if patient_id not in self.last_alert_time:
            return True
        elapsed = (datetime.utcnow() - self.last_alert_time[patient_id]).total_seconds()
        return elapsed > self.alert_cooldown

    def _send_alert(self, patient, severity, alert_type, message):
        """Send alert and store in database"""
        roles = []
        if severity == "CRITICAL":
            roles = ["doctor", "staff"]
        elif severity == "WARNING":
            roles = ["staff"]
        elif severity == "SOS":
            roles = ["doctor", "staff", "admin"]
            
        full_msg = f"[{severity}] Patient: {patient.name} (ID: {patient.id}) - {message}"
        
        # Store in database
        try:
            alert = Alert(
                patient_id=patient.id,
                severity=severity.lower(),
                alert_type=alert_type,
                message=message,
                sent_to_roles=','.join(roles)
            )
            db.session.add(alert)
            db.session.commit()
        except Exception as e:
            self.logger.error(f"Failed to store alert in database: {e}")
            db.session.rollback()
        
        # Mock Sending (console output)
        print(f"\n[SMS ALERT SYSTEM] ----------------------------------------")
        print(f"To Roles: {', '.join(roles)}")
        print(f"Message: {full_msg}")
        print(f"Timestamp: {datetime.utcnow()}")
        print(f"--------------------------------------------------------------\n")
        
        self.logger.info(f"Alert sent for patient {patient.id}: {message} to {roles}")
    
    def trigger_sos(self, patient, trigger_type='patient_triggered', vitals_snapshot=None):
        """
        Trigger SOS alert
        
        Args:
            patient: Patient object
            trigger_type: 'patient_triggered', 'vitals_critical', 'system_failure'
            vitals_snapshot: Dict of current vitals
        """
        message = f"SOS ALERT: {patient.name} - {trigger_type.replace('_', ' ').title()}"
        
        # Store SOS in database
        try:
            sos = SOSAlert(
                patient_id=patient.id,
                trigger_type=trigger_type,
                message=message,
                vitals_snapshot=vitals_snapshot
            )
            db.session.add(sos)
            db.session.commit()
        except Exception as e:
            self.logger.error(f"Failed to store SOS alert: {e}")
            db.session.rollback()
        
        # Send as critical alert
        self._send_alert(patient, "SOS", "sos_alert", message)
        
        return sos

