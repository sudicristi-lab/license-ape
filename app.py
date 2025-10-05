"""
License Management System - Main Flask Application
Handles license activation, validation, and admin management
"""

import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

import jwt
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///license_system.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', secrets.token_hex(32))
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'
csrf = CSRFProtect(app)

# Import models after db initialization
from models import AdminUser, License, Device, AuditLog

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))

# JWT Authentication decorator
def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

# -------------------
# API Routes
# -------------------

@app.route("/")
def home():
    return "License Management System server is running!"

@app.route('/activate', methods=['POST'])
def activate_license():
    """
    Activate a license for a device
    Expected JSON: {"license_key": "string", "device_id": "string", "device_info": "string"}
    """
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['license_key', 'device_id']):
            return jsonify({'error': 'Missing required fields'}), 400

        license_key = data['license_key']
        device_id = data['device_id']
        device_info = data.get('device_info', '')

        license_obj = License.query.filter_by(key=license_key).first()
        if not license_obj:
            return jsonify({'error': 'Invalid license key'}), 404

        if license_obj.status != 'active':
            return jsonify({'error': 'License is not active'}), 400

        if license_obj.expires_at and license_obj.expires_at < datetime.utcnow():
            license_obj.status = 'expired'
            db.session.commit()
            return jsonify({'error': 'License has expired'}), 400

        existing_device = Device.query.filter_by(device_id=device_id).first()
        if existing_device:
            if existing_device.license_id == license_obj.id:
                token = jwt.encode({
                    'user_id': device_id,
                    'license_id': license_obj.id,
                    'exp': datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
                }, app.config['JWT_SECRET_KEY'], algorithm='HS256')
                return jsonify({
                    'success': True,
                    'token': token,
                    'license_status': license_obj.status,
                    'expires_at': license_obj.expires_at.isoformat() if license_obj.expires_at else None
                })
            else:
                return jsonify({'error': 'Device already registered with different license'}), 400

        device = Device(
            device_id=device_id,
            license_id=license_obj.id,
            device_info=device_info,
            registered_at=datetime.utcnow()
        )
        db.session.add(device)

        audit_log = AuditLog(
            action='license_activated',
            license_id=license_obj.id,
            device_id=device_id,
            details=f'Device {device_id} activated license {license_key}'
        )
        db.session.add(audit_log)
        db.session.commit()

        token = jwt.encode({
            'user_id': device_id,
            'license_id': license_obj.id,
            'exp': datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
        }, app.config['JWT_SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'success': True,
            'token': token,
            'license_status': license_obj.status,
            'expires_at': license_obj.expires_at.isoformat() if license_obj.expires_at else None
        })

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/validate', methods=['POST'])
@jwt_required
def validate_license(user_id):
    """
    Validate a license for a device
    Requires JWT token in Authorization header
    """
    try:
        device = Device.query.filter_by(device_id=user_id).first()
        if not device:
            return jsonify({'error': 'Device not found'}), 404

        license_obj = License.query.get(device.license_id)
        if not license_obj:
            return jsonify({'error': 'License not found'}), 404

        if license_obj.status != 'active':
            return jsonify({'error': 'License is not active', 'status': license_obj.status}), 400

        if license_obj.expires_at and license_obj.expires_at < datetime.utcnow():
            license_obj.status = 'expired'
            db.session.commit()
            return jsonify({'error': 'License has expired', 'status': 'expired'}), 400

        device.last_validated = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'valid': True,
            'license_status': license_obj.status,
            'expires_at': license_obj.expires_at.isoformat() if license_obj.expires_at else None,
            'days_remaining': (license_obj.expires_at - datetime.utcnow()).days if license_obj.expires_at else None
        })

    except Exception:
        return jsonify({'error': 'Internal server error'}), 500


# -------------------
# Admin Routes
# -------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        admin = AdminUser.query.filter_by(username=username).first()
        if admin and check_password_hash(admin.password_hash, password):
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('admin/login.html')


@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))


@app.route('/admin')
@login_required
def admin_dashboard():
    licenses = License.query.all()
    devices = Device.query.all()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html', licenses=licenses, devices=devices, recent_logs=recent_logs)


@app.route('/admin/licenses')
@login_required
def admin_licenses():
    licenses = License.query.all()
    return render_template('admin/licenses.html', licenses=licenses)


@app.route('/admin/licenses/create', methods=['POST'])
@login_required
def create_license():
    try:
        key = request.form.get('key')
        duration_days = int(request.form.get('duration_days', 7))

        if not key:
            flash('License key is required', 'error')
            return redirect(url_for('admin_licenses'))

        if License.query.filter_by(key=key).first():
            flash('License key already exists', 'error')
            return redirect(url_for('admin_licenses'))

        expires_at = datetime.utcnow() + timedelta(days=duration_days)
        license_obj = License(key=key, status='active', expires_at=expires_at, created_by=current_user.id)
        db.session.add(license_obj)
        db.session.commit()

        flash('License created successfully', 'success')
        return redirect(url_for('admin_licenses'))

    except Exception as e:
    # log sau return error
    print(e)
    return jsonify({'error': 'Internal server error'}), 500

