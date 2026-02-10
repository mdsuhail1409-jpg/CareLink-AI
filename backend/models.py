from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and role-based access"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'doctor', 'staff', 'patient', 'admin'
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    # If user is a patient, link to patient record
    patient_profile = db.relationship('Patient', backref='user', uselist=False, foreign_keys='Patient.user_id')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Patient(db.Model):
    """Patient medical record"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for simulator patients
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    blood_type = db.Column(db.String(5))
    
    # Medical history flags (for AI prediction)
    has_hypertension = db.Column(db.Boolean, default=False)
    has_heart_disease = db.Column(db.Boolean, default=False)
    has_diabetes = db.Column(db.Boolean, default=False)
    smoking_status = db.Column(db.String(20))  # 'never', 'former', 'current'
    
    # Assignment
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assigned_doctor = db.relationship('User', foreign_keys=[assigned_doctor_id])
    
    # Relationships
    vitals_logs = db.relationship('VitalsLog', backref='patient', lazy=True)
    medications = db.relationship('Medication', backref='patient', lazy=True)
    disease_risks = db.relationship('DiseaseRiskLog', backref='patient', lazy=True)
    alerts = db.relationship('Alert', backref='patient', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'blood_type': self.blood_type,
            'has_hypertension': self.has_hypertension,
            'has_heart_disease': self.has_heart_disease,
            'has_diabetes': self.has_diabetes,
            'smoking_status': self.smoking_status,
            'assigned_doctor_id': self.assigned_doctor_id
        }

class VitalsLog(db.Model):
    """Historical vitals data"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    heart_rate = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    spo2 = db.Column(db.Integer)
    blood_pressure_systolic = db.Column(db.Integer)
    blood_pressure_diastolic = db.Column(db.Integer)
    respiratory_rate = db.Column(db.Integer)
    risk = db.Column(db.Integer)  # 0 = Normal, 1 = Warning, 2 = Critical

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'timestamp': self.timestamp.isoformat(),
            'heart_rate': self.heart_rate,
            'temperature': self.temperature,
            'spo2': self.spo2,
            'blood_pressure_systolic': self.blood_pressure_systolic,
            'blood_pressure_diastolic': self.blood_pressure_diastolic,
            'respiratory_rate': self.respiratory_rate,
            'risk': self.risk
        }

class DiseaseRiskLog(db.Model):
    """Multi-disease risk predictions"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Risk scores (0-1 probability or 0-100 percentage)
    heart_disease_risk = db.Column(db.Float)
    breast_cancer_risk = db.Column(db.Float)
    lung_cancer_risk = db.Column(db.Float)
    stroke_risk = db.Column(db.Float)
    sepsis_risk = db.Column(db.Float)
    ckd_risk = db.Column(db.Float)
    arrhythmia_risk = db.Column(db.Float)
    
    # Overall risk level
    overall_risk = db.Column(db.String(20))  # 'normal', 'warning', 'critical'
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'heart_disease_risk': self.heart_disease_risk,
            'breast_cancer_risk': self.breast_cancer_risk,
            'lung_cancer_risk': self.lung_cancer_risk,
            'stroke_risk': self.stroke_risk,
            'sepsis_risk': self.sepsis_risk,
            'ckd_risk': self.ckd_risk,
            'arrhythmia_risk': self.arrhythmia_risk,
            'overall_risk': self.overall_risk
        }

class Medication(db.Model):
    """Prescribed medications"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False, index=True)
    prescribed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    prescribed_by = db.relationship('User', foreign_keys=[prescribed_by_id])
    
    name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50))
    frequency = db.Column(db.String(50))  # e.g., "twice daily", "every 8 hours"
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    
    # Relationships
    logs = db.relationship('MedicationLog', backref='medication', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'prescribed_by_id': self.prescribed_by_id,
            'name': self.name,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_active': self.is_active,
            'notes': self.notes
        }

class MedicationLog(db.Model):
    """Medication adherence tracking"""
    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey('medication.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    status = db.Column(db.String(20), nullable=False)  # 'taken', 'missed', 'skipped'
    notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'medication_id': self.medication_id,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status,
            'notes': self.notes
        }

class Alert(db.Model):
    """Alert history"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    severity = db.Column(db.String(20), nullable=False)  # 'warning', 'critical', 'sos'
    alert_type = db.Column(db.String(50), nullable=False)  # 'sustained_hypoxia', 'rapid_deterioration', etc.
    message = db.Column(db.Text, nullable=False)
    
    # Routing
    sent_to_roles = db.Column(db.String(100))  # Comma-separated: 'doctor,staff,admin'
    
    # Status
    is_acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'alert_type': self.alert_type,
            'message': self.message,
            'sent_to_roles': self.sent_to_roles.split(',') if self.sent_to_roles else [],
            'is_acknowledged': self.is_acknowledged,
            'acknowledged_by_id': self.acknowledged_by_id,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }

class SOSAlert(db.Model):
    """Emergency SOS alerts"""
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    trigger_type = db.Column(db.String(50), nullable=False)  # 'patient_triggered', 'vitals_critical', 'system_failure'
    message = db.Column(db.Text, nullable=False)
    vitals_snapshot = db.Column(db.JSON)  # Store vitals at time of SOS
    
    # Status
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'timestamp': self.timestamp.isoformat(),
            'trigger_type': self.trigger_type,
            'message': self.message,
            'vitals_snapshot': self.vitals_snapshot,
            'is_resolved': self.is_resolved,
            'resolved_by_id': self.resolved_by_id,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_notes': self.resolution_notes
        }

class Message(db.Model):
    """Patient-Doctor messaging"""
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    recipient = db.relationship('User', foreign_keys=[recipient_id])
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'patient_id': self.patient_id,
            'timestamp': self.timestamp.isoformat(),
            'subject': self.subject,
            'message': self.message,
            'is_read': self.is_read
        }
