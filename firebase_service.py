"""
Firebase Cloud Messaging service for sending push notifications
"""

import os
import json
from typing import List, Dict, Optional
import firebase_admin
from firebase_admin import credentials, messaging
from flask import current_app

class FirebaseService:
    """Service class for handling Firebase Cloud Messaging operations"""
    
    def __init__(self):
        self.app = None
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if firebase_admin._apps:
                self.app = firebase_admin.get_app()
                return
            
            # Get Firebase credentials from environment
            firebase_credentials = os.getenv('FIREBASE_CREDENTIALS')
            
            if firebase_credentials:
                # Parse JSON credentials from environment variable
                cred_dict = json.loads(firebase_credentials)
                cred = credentials.Certificate(cred_dict)
            else:
                # Try to load from file
                cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                else:
                    current_app.logger.warning("Firebase credentials not found. FCM will be disabled.")
                    return
            
            # Initialize Firebase Admin SDK
            self.app = firebase_admin.initialize_app(cred)
            current_app.logger.info("Firebase Admin SDK initialized successfully")
            
        except Exception as e:
            current_app.logger.error(f"Failed to initialize Firebase: {str(e)}")
            self.app = None
    
    def send_notification_to_device(self, fcm_token: str, title: str, body: str, 
                                  data: Optional[Dict] = None) -> bool:
        """
        Send notification to a specific device
        
        Args:
            fcm_token: FCM token of the target device
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.app:
            current_app.logger.warning("Firebase not initialized. Cannot send notification.")
            return False
        
        try:
            # Create the message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=fcm_token
            )
            
            # Send the message
            response = messaging.send(message)
            current_app.logger.info(f"Successfully sent message: {response}")
            return True
            
        except messaging.UnregisteredError:
            current_app.logger.warning(f"FCM token is unregistered: {fcm_token}")
            return False
        except Exception as e:
            current_app.logger.error(f"Failed to send notification: {str(e)}")
            return False
    
    def send_notification_to_multiple_devices(self, fcm_tokens: List[str], title: str, 
                                            body: str, data: Optional[Dict] = None) -> Dict:
        """
        Send notification to multiple devices
        
        Args:
            fcm_tokens: List of FCM tokens
            title: Notification title
            body: Notification body
            data: Optional data payload
            
        Returns:
            Dict with success/failure counts
        """
        if not self.app:
            current_app.logger.warning("Firebase not initialized. Cannot send notifications.")
            return {'success': 0, 'failure': len(fcm_tokens)}
        
        if not fcm_tokens:
            return {'success': 0, 'failure': 0}
        
        try:
            # Create the message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                tokens=fcm_tokens
            )
            
            # Send the message
            response = messaging.send_multicast(message)
            
            result = {
                'success': response.success_count,
                'failure': response.failure_count,
                'responses': []
            }
            
            # Log individual responses
            for i, resp in enumerate(response.responses):
                if resp.success:
                    current_app.logger.info(f"Message {i} sent successfully: {resp.message_id}")
                else:
                    current_app.logger.error(f"Message {i} failed: {resp.exception}")
                
                result['responses'].append({
                    'success': resp.success,
                    'message_id': resp.message_id if resp.success else None,
                    'error': str(resp.exception) if not resp.success else None
                })
            
            return result
            
        except Exception as e:
            current_app.logger.error(f"Failed to send multicast notification: {str(e)}")
            return {'success': 0, 'failure': len(fcm_tokens)}
    
    def send_license_revocation_notification(self, device_id: str, license_key: str) -> bool:
        """
        Send notification when a license is revoked
        
        Args:
            device_id: Device ID
            license_key: License key that was revoked
            
        Returns:
            bool: True if successful, False otherwise
        """
        from models import Device
        
        # Find device and get FCM token
        device = Device.query.filter_by(device_id=device_id).first()
        if not device or not device.fcm_token:
            current_app.logger.warning(f"No FCM token found for device: {device_id}")
            return False
        
        title = "License Revoked"
        body = f"Your license {license_key} has been revoked. Please contact support."
        data = {
            'type': 'license_revoked',
            'license_key': license_key,
            'device_id': device_id
        }
        
        return self.send_notification_to_device(device.fcm_token, title, body, data)
    
    def send_license_expiry_notification(self, device_id: str, license_key: str, days_remaining: int) -> bool:
        """
        Send notification when a license is about to expire
        
        Args:
            device_id: Device ID
            license_key: License key
            days_remaining: Days remaining until expiry
            
        Returns:
            bool: True if successful, False otherwise
        """
        from models import Device
        
        # Find device and get FCM token
        device = Device.query.filter_by(device_id=device_id).first()
        if not device or not device.fcm_token:
            current_app.logger.warning(f"No FCM token found for device: {device_id}")
            return False
        
        title = "License Expiring Soon"
        body = f"Your license {license_key} expires in {days_remaining} days."
        data = {
            'type': 'license_expiring',
            'license_key': license_key,
            'device_id': device_id,
            'days_remaining': str(days_remaining)
        }
        
        return self.send_notification_to_device(device.fcm_token, title, body, data)
    
    def send_admin_notification(self, device_id: str, title: str, message: str) -> bool:
        """
        Send admin notification to a device
        
        Args:
            device_id: Device ID
            title: Notification title
            message: Notification message
            
        Returns:
            bool: True if successful, False otherwise
        """
        from models import Device
        
        # Find device and get FCM token
        device = Device.query.filter_by(device_id=device_id).first()
        if not device or not device.fcm_token:
            current_app.logger.warning(f"No FCM token found for device: {device_id}")
            return False
        
        data = {
            'type': 'admin_message',
            'device_id': device_id
        }
        
        return self.send_notification_to_device(device.fcm_token, title, message, data)

# Global Firebase service instance
firebase_service = FirebaseService()
