"""
Client Manager Module
-------------------
Handles all client-related operations including:
- Client creation and management
- Client data validation
- Client file initialization and maintenance
"""

import pandas as pd
import os
import logging
from datetime import datetime
from services.notification_service import NotificationService

class ClientManager:
    def __init__(self):
        self.clients_file = "clients.csv"
        self.setup_logging()
        self.initialize_clients_db()
        self.notification_service = NotificationService()

    def setup_logging(self):
        logging.basicConfig(
            filename='client_manager.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def initialize_clients_db(self):
        """Initialize clients database if it doesn't exist"""
        if not os.path.exists(self.clients_file):
            self.logger.info("Creating new clients database")
            df = pd.DataFrame(columns=[
                'id', 'name', 'email', 'phone', 
                'created_at', 'last_updated'
            ])
            df.to_csv(self.clients_file, index=False)
        self.clients_df = pd.read_csv(self.clients_file)

    def add_client(self, name, email, phone=None):
        """Add new client with validation and welcome email"""
        try:
            # Validate email format
            if '@' not in email or '.' not in email:
                raise ValueError("Invalid email format")

            # Check for existing email
            if not self.clients_df.empty and email in self.clients_df['email'].values:
                raise ValueError("Email already exists")

            new_client = {
                'id': len(self.clients_df) + 1,
                'name': name,
                'email': email,
                'phone': phone if phone else '',
                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            self.clients_df = pd.concat([
                self.clients_df, 
                pd.DataFrame([new_client])
            ], ignore_index=True)
            self.clients_df.to_csv(self.clients_file, index=False)
            
            # Send welcome email
            self.notification_service.send_welcome_email(name, email)
            
            self.logger.info(f"Added new client and sent welcome email: {name} ({email})")
            return True, new_client['id']

        except Exception as e:
            self.logger.error(f"Error adding client: {str(e)}")
            return False, str(e)

    def get_client_by_name(self, name):
        """Retrieve client details by name"""
        try:
            client = self.clients_df[self.clients_df['name'] == name]
            if client.empty:
                return None
            return client.iloc[0].to_dict()
        except Exception as e:
            self.logger.error(f"Error retrieving client: {str(e)}")
            return None

    def get_client_email(self, name):
        """Get client email by name"""
        client = self.get_client_by_name(name)
        return client['email'] if client else None
