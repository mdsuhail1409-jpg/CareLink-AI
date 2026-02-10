"""
Initialize demo data for CareLink AI system
Creates demo users, patients, and assignments
"""
from models import db, User, Patient
from auth import AuthService
import random

def init_demo_data(app):
    """Initialize demo users and patients"""
    with app.app_context():
        # Check if data already exists
        if User.query.first():
            print("Demo data already exists. Skipping initialization.")
            return
        
        print("Initializing demo data...")
        
        # Create Admin
        print("Creating admin user...")
        AuthService.register_user(
            email='admin@carelink.ai',
            password='admin123',
            role='admin',
            first_name='System',
            last_name='Administrator',
            phone='+1-555-0100'
        )
        
        # Create Doctors
        print("Creating doctors...")
        doctors = []
        doctor_data = [
            {'email': 'dr.smith@carelink.ai', 'first': 'John', 'last': 'Smith', 'phone': '+1-555-0101'},
            {'email': 'dr.johnson@carelink.ai', 'first': 'Emily', 'last': 'Johnson', 'phone': '+1-555-0102'},
            {'email': 'dr.williams@carelink.ai', 'first': 'Michael', 'last': 'Williams', 'phone': '+1-555-0103'}
        ]
        
        for doc in doctor_data:
            success, msg, user = AuthService.register_user(
                email=doc['email'],
                password='doctor123',
                role='doctor',
                first_name=doc['first'],
                last_name=doc['last'],
                phone=doc['phone']
            )
            if success:
                doctors.append(user)
        
        # Create Healthcare Staff
        print("Creating healthcare staff...")
        staff_data = [
            {'email': 'nurse.davis@carelink.ai', 'first': 'Sarah', 'last': 'Davis', 'phone': '+1-555-0201'},
            {'email': 'nurse.miller@carelink.ai', 'first': 'James', 'last': 'Miller', 'phone': '+1-555-0202'},
            {'email': 'nurse.wilson@carelink.ai', 'first': 'Lisa', 'last': 'Wilson', 'phone': '+1-555-0203'}
        ]
        
        for staff in staff_data:
            AuthService.register_user(
                email=staff['email'],
                password='staff123',
                role='staff',
                first_name=staff['first'],
                last_name=staff['last'],
                phone=staff['phone']
            )
        
        # Create Patients
        print("Creating patients...")
        patient_names = [
            ('Robert', 'Anderson', 'M', 65),
            ('Mary', 'Thomas', 'F', 58),
            ('David', 'Martinez', 'M', 72),
            ('Jennifer', 'Garcia', 'F', 45),
            ('William', 'Rodriguez', 'M', 68),
            ('Linda', 'Lopez', 'F', 54),
            ('Richard', 'Hernandez', 'M', 61),
            ('Patricia', 'Gonzalez', 'F', 70),
            ('Charles', 'Perez', 'M', 48),
            ('Barbara', 'Taylor', 'F', 63)
        ]
        
        blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        smoking_statuses = ['never', 'former', 'current']
        
        patients_created = []
        for i, (first, last, gender, age) in enumerate(patient_names):
            patient_data = {
                'age': age,
                'gender': gender,
                'blood_type': random.choice(blood_types),
                'has_hypertension': random.choice([True, False]),
                'has_heart_disease': random.choice([True, False]) if age > 60 else False,
                'has_diabetes': random.choice([True, False]) if age > 50 else False,
                'smoking_status': random.choice(smoking_statuses)
            }
            
            success, msg, user = AuthService.register_user(
                email=f'patient{i+1}@example.com',
                password='patient123',
                role='patient',
                first_name=first,
                last_name=last,
                phone=f'+1-555-03{i:02d}',
                patient_data=patient_data
            )
            
            if success:
                patients_created.append(user.patient_profile)
        
        # Assign patients to doctors (round-robin)
        print("Assigning patients to doctors...")
        for i, patient in enumerate(patients_created):
            doctor = doctors[i % len(doctors)]
            AuthService.assign_patient_to_doctor(patient.id, doctor.id)
        
        # Also create simulator patients (for backward compatibility)
        print("Creating simulator-only patients...")
        simulator_patients = [
            "John Doe", "Jane Smith", "Alice Johnson", "Bob Brown",
            "Charlie Davis", "Eve Wilson", "Frank Miller", "Grace Lee",
            "Henry Taylor", "Ivy Clark"
        ]
        
        for i, name in enumerate(simulator_patients):
            # Check if patient already exists
            if not Patient.query.filter_by(name=name).first():
                patient = Patient(
                    # Don't set ID, let it auto-increment
                    name=name,
                    age=random.randint(25, 80),
                    gender=random.choice(['M', 'F']),
                    blood_type=random.choice(blood_types),
                    has_hypertension=random.choice([True, False]),
                    has_heart_disease=random.choice([True, False]),
                    has_diabetes=random.choice([True, False]),
                    smoking_status=random.choice(smoking_statuses)
                )
                # Assign to a doctor
                patient.assigned_doctor_id = doctors[i % len(doctors)].id
                db.session.add(patient)
        
        db.session.commit()
        
        print("\n" + "="*60)
        print("Demo data initialized successfully!")
        print("="*60)
        print("\nLogin Credentials:")
        print("\nAdmin:")
        print("  Email: admin@carelink.ai")
        print("  Password: admin123")
        print("\nDoctors:")
        print("  Email: dr.smith@carelink.ai")
        print("  Email: dr.johnson@carelink.ai")
        print("  Email: dr.williams@carelink.ai")
        print("  Password: doctor123")
        print("\nHealthcare Staff:")
        print("  Email: nurse.davis@carelink.ai")
        print("  Email: nurse.miller@carelink.ai")
        print("  Email: nurse.wilson@carelink.ai")
        print("  Password: staff123")
        print("\nPatients:")
        print("  Email: patient1@example.com through patient10@example.com")
        print("  Password: patient123")
        print("="*60 + "\n")

if __name__ == '__main__':
    from flask import Flask
    from models import db
    import os
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, 'db', 'carelink.db')
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        init_demo_data(app)
