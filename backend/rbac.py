from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from functools import wraps
from models import Patient

def require_role(*allowed_roles):
    """
    Decorator to require specific role(s) for route access
    
    Usage:
        @require_role('doctor')
        @require_role('doctor', 'admin')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role')
            
            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'Access denied',
                    'message': f'This endpoint requires one of the following roles: {", ".join(allowed_roles)}'
                }), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def require_patient_access(fn):
    """
    Decorator to ensure user can only access their own patient data
    Used for patient role endpoints
    """
    @wraps(fn)
    def wrapper(patient_id, *args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        user_id = claims.get('user_id')
        user_role = claims.get('role')
        
        # Admin can access any patient
        if user_role == 'admin':
            return fn(patient_id, *args, **kwargs)
        
        # Staff can access any patient
        if user_role == 'staff':
            return fn(patient_id, *args, **kwargs)
        
        # Doctor can access assigned patients
        if user_role == 'doctor':
            patient = Patient.query.get(patient_id)
            if patient and patient.assigned_doctor_id == user_id:
                return fn(patient_id, *args, **kwargs)
            return jsonify({
                'error': 'Access denied',
                'message': 'You can only access your assigned patients'
            }), 403
        
        # Patient can only access their own data
        if user_role == 'patient':
            patient = Patient.query.filter_by(user_id=user_id).first()
            if patient and patient.id == patient_id:
                return fn(patient_id, *args, **kwargs)
            return jsonify({
                'error': 'Access denied',
                'message': 'You can only access your own data'
            }), 403
        
        return jsonify({'error': 'Access denied'}), 403
    
    return wrapper

def require_assigned_patient(fn):
    """
    Decorator for doctor routes - ensures doctor can only access assigned patients
    """
    @wraps(fn)
    def wrapper(patient_id, *args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        user_id = claims.get('user_id')
        user_role = claims.get('role')
        
        # Admin can access any patient
        if user_role == 'admin':
            return fn(patient_id, *args, **kwargs)
        
        # Doctor must be assigned to patient
        if user_role == 'doctor':
            patient = Patient.query.get(patient_id)
            if not patient:
                return jsonify({'error': 'Patient not found'}), 404
            
            if patient.assigned_doctor_id != user_id:
                return jsonify({
                    'error': 'Access denied',
                    'message': 'This patient is not assigned to you'
                }), 403
            
            return fn(patient_id, *args, **kwargs)
        
        return jsonify({'error': 'Access denied'}), 403
    
    return wrapper

def get_user_patients(user_id, user_role):
    """
    Get list of patients accessible by user based on role
    
    Returns:
        List of Patient objects
    """
    if user_role == 'admin' or user_role == 'staff':
        # Admin and staff can see all patients
        return Patient.query.all()
    
    elif user_role == 'doctor':
        # Doctors see only assigned patients
        return Patient.query.filter_by(assigned_doctor_id=user_id).all()
    
    elif user_role == 'patient':
        # Patients see only themselves
        patient = Patient.query.filter_by(user_id=user_id).first()
        return [patient] if patient else []
    
    return []
