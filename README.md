# License Management System - Backend

A comprehensive license management system built with Flask, SQLAlchemy, and Firebase Cloud Messaging.

## Features

- **License Management**: Create, activate, validate, and revoke software licenses
- **Device Registration**: Track devices that activate licenses
- **Admin Panel**: Web-based administration interface
- **JWT Authentication**: Secure API access with JSON Web Tokens
- **Firebase Integration**: Push notifications for license events
- **Audit Logging**: Complete activity tracking
- **Multi-database Support**: SQLite, PostgreSQL, MySQL compatible

## API Endpoints

### Public Endpoints
- `POST /activate` - Activate a license for a device
- `POST /validate` - Validate a license (requires JWT)

### Admin Endpoints
- `GET /admin/login` - Admin login page
- `POST /admin/login` - Admin authentication
- `GET /admin` - Admin dashboard
- `GET /admin/licenses` - License management
- `POST /admin/licenses/create` - Create new license
- `POST /admin/licenses/<id>/revoke` - Revoke license
- `GET /admin/devices` - Device management
- `GET /admin/notifications` - Send notifications

## Quick Start

### 1. Clone and Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
cp env.example .env
# Edit .env with your configuration
```

### 3. Database Setup

```bash
# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

Default admin credentials:
- Username: `admin`
- Password: `admin123`

## Docker Deployment

### Using Docker Compose

```bash
docker-compose up -d
```

### Using Docker

```bash
docker build -t license-system .
docker run -p 5000:5000 --env-file .env license-system
```

## Production Deployment

### Railway

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

### Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn --bind 0.0.0.0:$PORT app:app`
5. Add environment variables

### VPS Deployment

1. Install Docker and Docker Compose on your VPS
2. Clone the repository
3. Configure environment variables
4. Run `docker-compose up -d`

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key | Yes |
| `JWT_SECRET_KEY` | JWT signing key | Yes |
| `DATABASE_URL` | Database connection string | Yes |
| `FIREBASE_CREDENTIALS` | Firebase service account JSON | No |
| `FIREBASE_CREDENTIALS_PATH` | Path to Firebase credentials file | No |

## Database Models

### AdminUser
- Admin users for managing the system
- Username, email, password hash
- Created licenses and audit logs

### License
- Software licenses with unique keys
- Status (active, expired, revoked)
- Expiration dates and relationships

### Device
- Registered devices with license associations
- FCM tokens for push notifications
- Validation tracking

### AuditLog
- Complete activity logging
- Action tracking with timestamps
- IP addresses and user agents

## Security Features

- **JWT Authentication**: Secure API access
- **CSRF Protection**: Form security
- **Password Hashing**: Secure password storage
- **HTTPS Ready**: Production security
- **Input Validation**: SQL injection prevention

## Firebase Integration

The system integrates with Firebase Cloud Messaging for:

- License revocation notifications
- License expiry warnings
- Admin messages
- System announcements

### Setup Firebase

1. Create a Firebase project
2. Enable Cloud Messaging
3. Generate service account credentials
4. Add credentials to environment variables

## API Usage Examples

### Activate License

```bash
curl -X POST http://localhost:5000/activate \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "LICENSE-123-ABC",
    "device_id": "device-123",
    "device_info": "Android 13, Samsung Galaxy S21"
  }'
```

### Validate License

```bash
curl -X POST http://localhost:5000/validate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Style

```bash
black .
flake8 .
```

### Database Migrations

```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

## Monitoring and Logging

The application includes comprehensive logging for:

- API requests and responses
- Authentication events
- License operations
- Firebase notifications
- Database operations
- Error tracking

## Troubleshooting

### Common Issues

1. **Database Connection**: Check DATABASE_URL format
2. **Firebase Errors**: Verify credentials and project setup
3. **JWT Issues**: Ensure JWT_SECRET_KEY is set
4. **CORS Problems**: Configure CORS_ORIGINS for API access

### Logs

Check application logs for detailed error information:

```bash
docker-compose logs web
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
