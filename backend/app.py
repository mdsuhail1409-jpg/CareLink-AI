from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt, get_jwt_identity
from simulator import Simulator
from predict import predict_risk, model as predictor_model
from models import db, User, Patient, VitalsLog, Medication, MedicationLog, Alert, SOSAlert, Message, DiseaseRiskLog
from auth import AuthService
from rbac import require_role, require_patient_access, require_assigned_patient, get_user_patients
import threading
import os
from datetime import datetime

# Set up paths for frontend serving
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
DB_PATH = os.path.join(BASE_DIR, 'db', 'carelink.db')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'carelink-ai-secret-key-change-in-production'  # Change in production!
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'

CORS(app)  # Enable CORS for frontend
db.init_app(app)
jwt = JWTManager(app)

# Create DB tables and initialize data
with app.app_context():
    db.create_all()
    # Initialize demo data if database is empty
    if not User.query.first():
        from init_data import init_demo_data
        init_demo_data(app)

# Initialize Simulator (Pass app context factory for DB access)
sim = Simulator(app)
sim.start()

# ============================================================================
# STATIC FILE SERVING
# ============================================================================

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from frontend directory."""
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    # If file doesn't exist, serve index.html (for SPA routing)
    return send_from_directory(FRONTEND_DIR, 'index.html')

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.json
    
    required_fields = ['email', 'password', 'role', 'first_name', 'last_name']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    patient_data = data.get('patient_data') if data['role'] == 'patient' else None
    
    success, message, user = AuthService.register_user(
        email=data['email'],
        password=data['password'],
        role=data['role'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone=data.get('phone'),
        patient_data=patient_data
    )
    
    if success:
        return jsonify({
            'message': message,
            'user': user.to_dict()
        }), 201
    else:
        return jsonify({'error': message}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    data = request.json
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    success, message, token, user = AuthService.login_user(
        email=data['email'],
        password=data['password']
    )
    
    if success:
        return jsonify({
            'message': message,
            'access_token': token,
            'user': user.to_dict()
        }), 200
    else:
        return jsonify({'error': message}), 401

@app.route('/api/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current authenticated user info"""
    user = AuthService.get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    response = user.to_dict()
    
    # If patient, include patient profile
    if user.role == 'patient' and user.patient_profile:
        response['patient'] = user.patient_profile.to_dict()
    
    return jsonify(response), 200

# ============================================================================
# PATIENT ROUTES (All roles with appropriate access control)
# ============================================================================

@app.route('/api/patients', methods=['GET'])
@jwt_required()
def get_patients():
    """Returns list of patients based on user role"""
    claims = get_jwt()
    user_id = claims.get('user_id')
    user_role = claims.get('role')
    
    patients = get_user_patients(user_id, user_role)
    
    data = []
    for patient in patients:
        # Get current vitals from simulator
        sim_patient = sim.get_patient(patient.id)
        if sim_patient:
            # Predict risk for each patient based on current vitals
            current_risk = predict_risk(sim_patient.heart_rate, sim_patient.temperature, sim_patient.spo2)
            
            p_data = {
                **patient.to_dict(),
                'heart_rate': int(sim_patient.heart_rate),
                'temperature': round(sim_patient.temperature, 1),
                'spo2': int(sim_patient.spo2),
                'risk': current_risk,
                'risk_label': "High Risk" if current_risk == 1 else "Normal",
                'trend': sim_patient.trend
            }
            data.append(p_data)
    
    return jsonify(data)

@app.route('/api/patient/<int:patient_id>', methods=['GET'])
@jwt_required()
@require_patient_access
def get_patient(patient_id):
    """Returns data for a specific patient"""
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({"error": "Patient not found"}), 404
    
    # Get current vitals from simulator
    sim_patient = sim.get_patient(patient_id)
    if not sim_patient:
        return jsonify({"error": "Patient vitals not available"}), 404
    
    current_risk = predict_risk(sim_patient.heart_rate, sim_patient.temperature, sim_patient.spo2)
    
    p_data = {
        **patient.to_dict(),
        'heart_rate': int(sim_patient.heart_rate),
        'temperature': round(sim_patient.temperature, 1),
        'spo2': int(sim_patient.spo2),
        'risk': current_risk,
        'risk_label': "High Risk" if current_risk == 1 else "Normal",
        'trend': sim_patient.trend
    }
    
    return jsonify(p_data)

@app.route('/api/patient/<int:patient_id>/history', methods=['GET'])
@jwt_required()
@require_patient_access
def get_patient_history(patient_id):
    """Returns historical vitals for a patient."""
    limit = request.args.get('limit', 50, type=int)
    logs = VitalsLog.query.filter_by(patient_id=patient_id).order_by(VitalsLog.timestamp.desc()).limit(limit).all()
    history = [log.to_dict() for log in logs]
    return jsonify(history)

@app.route('/api/patient/<int:patient_id>/trend', methods=['POST'])
@jwt_required()
@require_role('doctor', 'admin')
def set_patient_trend(patient_id):
    """Sets the simulation trend for a patient (Doctor/Admin only)"""
    sim_patient = sim.get_patient(patient_id)
    if not sim_patient:
        return jsonify({"error": "Patient not found"}), 404
        
    data = request.json
    trend = data.get('trend')
    if trend not in ["STABLE", "DETERIORATING", "RECOVERING"]:
        return jsonify({"error": "Invalid trend type"}), 400
        
    sim_patient.trend = trend
    return jsonify({"success": True, "message": f"Trend set to {trend}", "patient": sim_patient.name})

@app.route('/api/patient/<int:patient_id>/forecast', methods=['GET'])
@jwt_required()
@require_role('doctor', 'admin')
def get_patient_forecast(patient_id):
    """Returns future vitals prediction (Doctor/Admin only)"""
    sim_patient = sim.get_patient(patient_id)
    if not sim_patient:
        return jsonify({"error": "Patient not found"}), 404
    
    # Generate forecasts for +15, +30, +45, +60 minutes
    forecasts = []
    times = [15, 30, 45, 60]
    
    for t in times:
        pred_vitals = sim_patient.predict_future(minutes=t)
        # Predict risk for this future state
        pred_risk = predict_risk(pred_vitals['heart_rate'], pred_vitals['temperature'], pred_vitals['spo2'])
        
        forecasts.append({
            "minutes_ahead": t,
            "vitals": pred_vitals,
            "risk": pred_risk,
            "risk_label": "High Risk" if pred_risk == 1 else "Normal"
        })
        
    return jsonify({
        "patient_id": sim_patient.id,
        "name": sim_patient.name,
        "current_trend": sim_patient.trend,
        "forecast": forecasts
    })

# ============================================================================
# DOCTOR ROUTES
# ============================================================================

@app.route('/api/doctor/patients', methods=['GET'])
@jwt_required()
@require_role('doctor')
def get_doctor_patients():
    """Get all patients assigned to the logged-in doctor"""
    claims = get_jwt()
    doctor_id = claims.get('user_id')
    
    patients = Patient.query.filter_by(assigned_doctor_id=doctor_id).all()
    
    data = []
    for patient in patients:
        sim_patient = sim.get_patient(patient.id)
        if sim_patient:
            current_risk = predict_risk(sim_patient.heart_rate, sim_patient.temperature, sim_patient.spo2)
            p_data = {
                **patient.to_dict(),
                'heart_rate': int(sim_patient.heart_rate),
                'temperature': round(sim_patient.temperature, 1),
                'spo2': int(sim_patient.spo2),
                'risk': current_risk,
                'risk_label': "High Risk" if current_risk == 1 else "Normal",
                'trend': sim_patient.trend
            }
            data.append(p_data)
    
    return jsonify(data)

@app.route('/api/doctor/patient/<int:patient_id>/medication', methods=['POST'])
@jwt_required()
@require_role('doctor')
@require_assigned_patient
def prescribe_medication(patient_id):
    """Prescribe medication to a patient"""
    claims = get_jwt()
    doctor_id = claims.get('user_id')
    data = request.json
    
    required_fields = ['name', 'dosage', 'frequency']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    medication = Medication(
        patient_id=patient_id,
        prescribed_by_id=doctor_id,
        name=data['name'],
        dosage=data['dosage'],
        frequency=data['frequency'],
        notes=data.get('notes', '')
    )
    
    db.session.add(medication)
    db.session.commit()
    
    return jsonify({
        'message': 'Medication prescribed successfully',
        'medication': medication.to_dict()
    }), 201

@app.route('/api/doctor/alerts', methods=['GET'])
@jwt_required()
@require_role('doctor')
def get_doctor_alerts():
    """Get alerts for doctor's assigned patients"""
    claims = get_jwt()
    doctor_id = claims.get('user_id')
    
    # Get all patients assigned to this doctor
    patient_ids = [p.id for p in Patient.query.filter_by(assigned_doctor_id=doctor_id).all()]
    
    # Get recent alerts for these patients
    alerts = Alert.query.filter(
        Alert.patient_id.in_(patient_ids),
        Alert.is_acknowledged == False
    ).order_by(Alert.timestamp.desc()).limit(50).all()
    
    return jsonify([alert.to_dict() for alert in alerts])

# ============================================================================
# STAFF ROUTES
# ============================================================================

@app.route('/api/staff/patients', methods=['GET'])
@jwt_required()
@require_role('staff')
def get_staff_patients():
    """Get all patients (staff can monitor all)"""
    patients = Patient.query.all()
    
    data = []
    for patient in patients:
        sim_patient = sim.get_patient(patient.id)
        if sim_patient:
            p_data = {
                **patient.to_dict(),
                'heart_rate': int(sim_patient.heart_rate),
                'temperature': round(sim_patient.temperature, 1),
                'spo2': int(sim_patient.spo2),
                'trend': sim_patient.trend
            }
            data.append(p_data)
    
    return jsonify(data)

@app.route('/api/staff/alerts', methods=['GET'])
@jwt_required()
@require_role('staff')
def get_staff_alerts():
    """Get all unacknowledged alerts"""
    alerts = Alert.query.filter_by(is_acknowledged=False).order_by(Alert.timestamp.desc()).limit(100).all()
    return jsonify([alert.to_dict() for alert in alerts])

@app.route('/api/staff/alert/<int:alert_id>/acknowledge', methods=['POST'])
@jwt_required()
@require_role('staff', 'doctor', 'admin')
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    claims = get_jwt()
    user_id = claims.get('user_id')
    
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    
    alert.is_acknowledged = True
    alert.acknowledged_by_id = user_id
    alert.acknowledged_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Alert acknowledged', 'alert': alert.to_dict()})

# ============================================================================
# PATIENT SELF-SERVICE ROUTES
# ============================================================================

@app.route('/api/patient/me', methods=['GET'])
@jwt_required()
@require_role('patient')
def get_my_patient_data():
    """Get own patient data"""
    user = AuthService.get_current_user()
    if not user.patient_profile:
        return jsonify({'error': 'Patient profile not found'}), 404
    
    patient = user.patient_profile
    sim_patient = sim.get_patient(patient.id)
    
    if not sim_patient:
        return jsonify({'error': 'Vitals not available'}), 404
    
    current_risk = predict_risk(sim_patient.heart_rate, sim_patient.temperature, sim_patient.spo2)
    
    return jsonify({
        **patient.to_dict(),
        'heart_rate': int(sim_patient.heart_rate),
        'temperature': round(sim_patient.temperature, 1),
        'spo2': int(sim_patient.spo2),
        'risk': current_risk,
        'risk_label': "High Risk" if current_risk == 1 else "Normal",
        'trend': sim_patient.trend
    })

@app.route('/api/patient/medications', methods=['GET'])
@jwt_required()
@require_role('patient')
def get_my_medications():
    """Get own medications"""
    user = AuthService.get_current_user()
    if not user.patient_profile:
        return jsonify({'error': 'Patient profile not found'}), 404
    
    medications = Medication.query.filter_by(
        patient_id=user.patient_profile.id,
        is_active=True
    ).all()
    
    return jsonify([med.to_dict() for med in medications])

@app.route('/api/patient/medication/<int:medication_id>/log', methods=['POST'])
@jwt_required()
@require_role('patient')
def log_medication(medication_id):
    """Log medication as taken/missed"""
    user = AuthService.get_current_user()
    data = request.json
    
    medication = Medication.query.get(medication_id)
    if not medication or medication.patient_id != user.patient_profile.id:
        return jsonify({'error': 'Medication not found'}), 404
    
    status = data.get('status')  # 'taken', 'missed', 'skipped'
    if status not in ['taken', 'missed', 'skipped']:
        return jsonify({'error': 'Invalid status'}), 400
    
    log = MedicationLog(
        medication_id=medication_id,
        status=status,
        notes=data.get('notes', '')
    )
    
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': 'Medication logged', 'log': log.to_dict()})

@app.route('/api/patient/sos', methods=['POST'])
@jwt_required()
@require_role('patient')
def trigger_sos():
    """Trigger SOS alert"""
    user = AuthService.get_current_user()
    if not user.patient_profile:
        return jsonify({'error': 'Patient profile not found'}), 404
    
    patient = user.patient_profile
    sim_patient = sim.get_patient(patient.id)
    
    vitals_snapshot = {
        'heart_rate': int(sim_patient.heart_rate) if sim_patient else None,
        'temperature': round(sim_patient.temperature, 1) if sim_patient else None,
        'spo2': int(sim_patient.spo2) if sim_patient else None
    }
    
    sos = SOSAlert(
        patient_id=patient.id,
        trigger_type='patient_triggered',
        message=f"SOS alert triggered by patient {patient.name}",
        vitals_snapshot=vitals_snapshot
    )
    
    db.session.add(sos)
    db.session.commit()
    
    # TODO: Send notifications to doctor, staff, admin
    
    return jsonify({
        'message': 'SOS alert sent',
        'sos': sos.to_dict()
    }), 201

# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/api/admin/users', methods=['GET'])
@jwt_required()
@require_role('admin')
def get_all_users():
    """Get all users"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@app.route('/api/admin/alerts', methods=['GET'])
@jwt_required()
@require_role('admin')
def get_all_alerts():
    """Get all alerts"""
    alerts = Alert.query.order_by(Alert.timestamp.desc()).limit(200).all()
    return jsonify([alert.to_dict() for alert in alerts])

@app.route('/api/admin/assign-patient', methods=['POST'])
@jwt_required()
@require_role('admin')
def admin_assign_patient():
    """Assign patient to doctor"""
    data = request.json
    patient_id = data.get('patient_id')
    doctor_id = data.get('doctor_id')
    
    success, message = AuthService.assign_patient_to_doctor(patient_id, doctor_id)
    
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 400

# ============================================================================
# LEGACY/DEBUG ROUTES
# ============================================================================

@app.route('/api/model-info', methods=['GET'])
def model_info():
    """Debug endpoint to check model status."""
    return jsonify({
        "model_loaded": predictor_model is not None,
        "model_type": str(type(predictor_model))
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
