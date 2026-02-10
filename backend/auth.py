from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from functools import wraps
from models import db, User, Patient
from datetime import timedelta

class AuthService:
    """Authentication service for user management"""
    
    @staticmethod
    def register_user(email, password, role, first_name, last_name, phone=None, patient_data=None):
        """
        Register a new user
        
        Args:
            email: User email
            password: Plain text password (will be hashed)
            role: User role ('doctor', 'staff', 'patient', 'admin')
            first_name: First name
            last_name: Last name
            phone: Phone number (optional)
            patient_data: Dict with patient medical data (required if role='patient')
        
        Returns:
            tuple: (success: bool, message: str, user: User or None)
        """
        # Validate role
        valid_roles = ['doctor', 'staff', 'patient', 'admin']
        if role not in valid_roles:
            return False, f"Invalid role. Must be one of: {', '.join(valid_roles)}", None
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return False, "Email already registered", None
        
        # Create user
        user = User(
            email=email,
            role=role,
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.flush()  # Get user.id before committing
            
            # If patient, create patient profile
            if role == 'patient':
                if not patient_data:
                    patient_data = {}
                
                patient = Patient(
                    user_id=user.id,
                    name=f"{first_name} {last_name}",
                    age=patient_data.get('age'),
                    gender=patient_data.get('gender'),
                    blood_type=patient_data.get('blood_type'),
                    has_hypertension=patient_data.get('has_hypertension', False),
                    has_heart_disease=patient_data.get('has_heart_disease', False),
                    has_diabetes=patient_data.get('has_diabetes', False),
                    smoking_status=patient_data.get('smoking_status', 'never')
                )
                db.session.add(patient)
            
            db.session.commit()
            return True, "User registered successfully", user
            
        except Exception as e:
            db.session.rollback()
            return False, f"Registration failed: {str(e)}", None
    
    @staticmethod
    def login_user(email, password):
        """
        Authenticate user and generate JWT token
        
        Returns:
            tuple: (success: bool, message: str, token: str or None, user: User or None)
        """
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return False, "Invalid email or password", None, None
        
        if not user.is_active:
            return False, "Account is deactivated", None, None
        
        if not user.check_password(password):
            return False, "Invalid email or password", None, None
        
        # Create JWT token with user info
        additional_claims = {
            'role': user.role,
            'user_id': user.id
        }
        access_token = create_access_token(
            identity=user.id,
            additional_claims=additional_claims,
            expires_delta=timedelta(hours=24)
        )
        
        return True, "Login successful", access_token, user
    
    @staticmethod
    def get_current_user():
        """Get current authenticated user from JWT"""
        user_id = get_jwt_identity()
        return User.query.get(user_id)
    
    @staticmethod
    def assign_patient_to_doctor(patient_id, doctor_id):
        """Assign a patient to a doctor"""
        patient = Patient.query.get(patient_id)
        doctor = User.query.filter_by(id=doctor_id, role='doctor').first()
        
        if not patient:
            return False, "Patient not found"
        
        if not doctor:
            return False, "Doctor not found"
        
        patient.assigned_doctor_id = doctor_id
        db.session.commit()
        
        return True, f"Patient {patient.name} assigned to Dr. {doctor.first_name} {doctor.last_name}"
