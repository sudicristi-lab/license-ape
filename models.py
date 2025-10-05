from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class AdminUser(UserMixin, db.Model):
    __tablename__ = 'admin_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relații explicit foreign_keys
    created_licenses = db.relationship(
        'License',
        foreign_keys='License.created_by',
        backref='creator',
        lazy='dynamic'
    )
    revoked_licenses = db.relationship(
        'License',
        foreign_keys='License.revoked_by',
        backref='revoker',
        lazy='dynamic'
    )

    audit_logs = db.relationship('AuditLog', back_populates='admin_user')

    def __repr__(self):
        return f'<AdminUser {self.username}>'

class License(db.Model):
    __tablename__ = 'licenses'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='active', nullable=False)
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    revoked_at = db.Column(db.DateTime)

    created_by = db.Column(db.Integer, db.ForeignKey('admin_users.id'))
    revoked_by = db.Column(db.Integer, db.ForeignKey('admin_users.id'))

    devices = db.relationship('Device', backref='license', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='license', lazy='dynamic')

    def __repr__(self):
        return f'<License {self.key}>'

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def days_remaining(self):
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.utcnow()
        return max(delta.days, 0)

class Device(db.Model):
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(255), nullable=False, index=True)
    device_info = db.Column(db.Text)
    fcm_token = db.Column(db.String(255))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_validated = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    license_id = db.Column(db.Integer, db.ForeignKey('licenses.id'), nullable=False)

    audit_logs = db.relationship('AuditLog', backref='device', lazy='dynamic')

    def __repr__(self):
        return f'<Device {self.device_id}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    license_id = db.Column(db.Integer, db.ForeignKey('licenses.id'))
    device_id = db.Column(db.String(255))
    admin_user_id = db.Column(db.Integer, db.ForeignKey('admin_users.id'))

    # Relație fără backref conflictual
    admin_user = db.relationship('AdminUser', back_populates='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.action} at {self.created_at}>'
