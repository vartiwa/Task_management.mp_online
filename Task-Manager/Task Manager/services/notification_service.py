"""
Notification Service Module
--------------------------
This module handles all notification-related functionality for the Task Manager system.
It supports multiple notification channels including email and in-app notifications.
Key features:
- Email notifications using SMTP
- Notification history tracking
- Waitlist notifications
- Appointment reminders
- Configurable notification templates
- Error handling and logging
"""

# Import required libraries for email handling and file operations
import json
import os
from datetime import datetime
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class NotificationService:
    def __init__(self):
        # Initialize file paths for notification storage and configuration
        self.notification_file = "notifications.json"
        self.config_file = "notification_config.json"
        self.load_notifications()
        self.config = self.load_config()
        self.setup_logging()
        self.load_email_templates()

    def setup_logging(self):
        # Setup logging for notification service
        logging.basicConfig(
            filename='notification_service.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def load_email_templates(self):
        # Enhanced email templates with dynamic content
        self.email_templates = {
            'welcome': """
                Dear {client_name},
                
                Welcome to our Task Manager! We're excited to have you on board.
                
                Your account has been successfully created with:
                Email: {client_email}
                
                You can now start booking appointments and managing your schedule.
                
                Best regards,
                Task Manager Team
            """,
            'reminder': """
                Dear {client_name},
                This is a reminder for your appointment scheduled on {appointment_date} at {appointment_time}.
                Appointment ID: {appointment_id}
                
                Best regards,
                Task Manager Team
            """,
            'waitlist': """
                Dear {client_name},
                Good news! A slot is now available on {date} that matches your preferences.
                Please log in to book your appointment.
                
                Best regards,
                Task Manager Team
            """
        }

    def load_config(self):
        # Load or create notification configuration with SMTP settings
        # Default config disables email functionality until properly configured
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        default_config = {
            'email_enabled': False,
            'smtp_server': '',
            'smtp_port': 587,
            'smtp_username': '',
            'smtp_password': '',
            'from_email': ''
        }
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f)
        return default_config

    def send_email(self, to_email, subject, message):
        """
        Send email with improved error handling and logging
        Args:
            to_email (str): Recipient's email address
            subject (str): Email subject
            message (str): Email body
        Returns:
            bool: Success status of email sending
        """
        if not self.config['email_enabled']:
            self.logger.warning("Email notifications are disabled in config")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['from_email']
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(message.strip(), 'plain'))

            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.starttls()
                server.login(self.config['smtp_username'], self.config['smtp_password'])
                server.send_message(msg)
            
            self.logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    def load_notifications(self):
        # Load notification history from JSON file or initialize empty list
        if os.path.exists(self.notification_file):
            with open(self.notification_file, 'r') as f:
                self.notifications = json.load(f)
        else:
            self.notifications = []

    def save_notifications(self):
        # Persist current notifications to JSON file
        with open(self.notification_file, 'w') as f:
            json.dump(self.notifications, f)

    def send_reminder(self, appointment_id, client_email, client_name, appointment_date, appointment_time):
        # Create and send appointment reminder with client details
        notification = {
            'type': 'reminder',
            'appointment_id': appointment_id,
            'client_email': client_email,
            'client_name': client_name,
            'sent_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'pending'
        }
        
        if client_email:
            message = self.email_templates['reminder'].format(
                client_name=client_name,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                appointment_id=appointment_id
            )
            
            email_sent = self.send_email(
                client_email,
                "Appointment Reminder",
                message
            )
            notification['status'] = 'sent' if email_sent else 'failed'

        self.notifications.append(notification)
        self.save_notifications()
        return notification['status'] == 'sent'

    def notify_waitlist(self, slot_details):
        # Notify waitlisted client about slot availability
        if 'client_email' not in slot_details:
            self.logger.warning(f"No email found for client {slot_details['client_name']}")
            return False

        message = self.email_templates['waitlist'].format(
            client_name=slot_details['client_name'],
            date=slot_details['date']
        )

        email_sent = self.send_email(
            slot_details['client_email'],
            "Slot Available - Task Manager",
            message
        )

        notification = {
            'type': 'waitlist',
            'client_name': slot_details['client_name'],
            'client_email': slot_details['client_email'],
            'date': slot_details['date'],
            'sent_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'status': 'sent' if email_sent else 'failed'
        }

        self.notifications.append(notification)
        self.save_notifications()
        return email_sent

    def get_notifications(self, client_name=None):
        # Retrieve all notifications or filter by client name
        # Returns notification history for reporting and tracking
        if client_name:
            return [n for n in self.notifications if n.get('client_name') == client_name]
        return self.notifications

    def send_welcome_email(self, client_name, client_email):
        """Send welcome email to new clients"""
        try:
            message = self.email_templates['welcome'].format(
                client_name=client_name,
                client_email=client_email
            )
            
            success = self.send_email(
                to_email=client_email,
                subject=f"Welcome to Task Manager, {client_name}!",
                message=message
            )
            
            if success:
                self.logger.info(f"Welcome email sent to {client_name} ({client_email})")
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to send welcome email: {str(e)}")
            return False
