# Import necessary libraries for date handling, data management, and file operations
from datetime import datetime, timedelta
import pandas as pd
import json
import os
from services.client_manager import ClientManager

class SchedulingEngine:
    def __init__(self):
        # Initialize file paths for storing scheduling data and configurations
        self.schedule_file = "appointments.csv"
        self.config_file = "scheduling_config.json"
        self.initialize_schedule()
        # Load working hours and slot duration from config, with default values if not found
        self.working_hours = self.load_config().get('working_hours', {'start': 9, 'end': 17})
        self.slot_duration = self.load_config().get('slot_duration', 60)
        self.waitlist_file = "waitlist.json"
        self.load_waitlist()
        self.client_manager = ClientManager()

    def initialize_schedule(self):
        # Create a new appointments file with required columns if it doesn't exist
        # Otherwise, load existing appointments data
        if not os.path.exists(self.schedule_file):
            self.appointments_df = pd.DataFrame(columns=[
                'id', 'client_name', 'professional_id', 'service_type',
                'start_time', 'duration', 'status', 'payment_status'
            ])
            self.appointments_df.to_csv(self.schedule_file, index=False)
        else:
            self.appointments_df = pd.read_csv(self.schedule_file)

    def load_waitlist(self):
        # Load the waitlist from JSON file or initialize an empty list if file doesn't exist
        if os.path.exists(self.waitlist_file):
            with open(self.waitlist_file, 'r') as f:
                self.waitlist = json.load(f)
        else:
            self.waitlist = []

    def save_waitlist(self):
        # Persist the current waitlist to JSON file
        with open(self.waitlist_file, 'w') as f:
            json.dump(self.waitlist, f)

    def load_config(self):
        # Load or create scheduling configuration with default values
        # Configuration includes working hours, slot duration, break duration, and notification settings
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        default_config = {
            'working_hours': {'start': 9, 'end': 17},
            'slot_duration': 60,
            'break_duration': 60,
            'notification_lead_time': 24  # hours before appointment
        }
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f)
        return default_config

    def update_config(self, new_config):
        # Update the scheduling configuration and save to file
        # Also update the current instance's working hours and slot duration
        config = self.load_config()
        config.update(new_config)
        with open(self.config_file, 'w') as f:
            json.dump(config, f)
        self.working_hours = config['working_hours']
        self.slot_duration = config['slot_duration']
        return True

    def check_availability(self, professional_id, date_str):
        # Convert input date string to datetime object
        date = datetime.strptime(date_str, "%Y-%m-%d")
        available_slots = []
        
        # Retrieve and parse professional's break times from their profile
        prof_df = pd.read_csv("professionals.csv")
        prof_breaks = prof_df[prof_df['id'] == int(professional_id)]['break_times'].iloc[0]
        break_times = [b.strip() for b in prof_breaks.split(',')] if prof_breaks != '' else []
        
        # Calculate day's start and end times based on working hours
        current_slot = datetime.combine(date.date(), 
                                      datetime.strptime(f"{self.working_hours['start']}:00", "%H:%M").time())
        end_time = datetime.combine(date.date(), 
                                  datetime.strptime(f"{self.working_hours['end']}:00", "%H:%M").time())

        # Iterate through all possible time slots in the day
        while current_slot < end_time:
            slot_end = current_slot + timedelta(minutes=self.slot_duration)
            time_str = current_slot.strftime("%H:%M")
            
            # Check if current slot overlaps with any break periods
            is_break = any(
                time_str >= break_start and time_str < break_end
                for break_period in break_times
                for break_start, break_end in [break_period.split('-')]
            )
            
            # Check if slot is already booked by querying appointments dataframe
            slot_booked = self.appointments_df[
                (self.appointments_df['professional_id'] == int(professional_id)) &
                (pd.to_datetime(self.appointments_df['start_time']).dt.strftime("%H:%M") == time_str)
            ].empty == False

            # Add slot to available slots if it's neither during a break nor booked
            if not (slot_booked or is_break):
                available_slots.append(time_str)
            
            current_slot = slot_end

        return available_slots

    def book_appointment(self, client_name, professional_id, service_type, date_str, time_str, client_email=None):
        """Book appointment with client management"""
        try:
            # Check/Create client record
            client = self.client_manager.get_client_by_name(client_name)
            if not client:
                if not client_email:
                    return False, "Client email is required for new clients"
                success, client_id = self.client_manager.add_client(client_name, client_email)
                if not success:
                    return False, f"Failed to create client: {client_id}"

            # Continue with existing booking logic
            start_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            
            if time_str not in self.check_availability(professional_id, date_str):
                return False, "Selected time slot is not available"

            # Create and add new appointment to the schedule
            next_id = len(self.appointments_df) + 1
            new_appointment = pd.DataFrame({
                'id': [next_id],
                'client_name': [client_name],
                'professional_id': [professional_id],
                'service_type': [service_type],
                'start_time': [start_time],
                'duration': [self.slot_duration],
                'status': ['scheduled'],
                'payment_status': ['pending']
            })

            self.appointments_df = pd.concat([self.appointments_df, new_appointment], ignore_index=True)
            self.appointments_df.to_csv(self.schedule_file, index=False)
            
            # Check waitlist for notifications
            self.check_waitlist_for_slot(professional_id, date_str)
            
            return True, f"Appointment booked successfully for {start_time}"

        except Exception as e:
            return False, f"Booking failed: {str(e)}"

    def add_to_waitlist(self, client_name, professional_id, preferred_dates):
        # Create a waitlist entry with client details and timestamp
        waitlist_entry = {
            'client_name': client_name,
            'professional_id': professional_id,
            'preferred_dates': preferred_dates,
            'added_on': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.waitlist.append(waitlist_entry)
        self.save_waitlist()
        return "Added to waitlist successfully"

    def check_waitlist_for_slot(self, professional_id, date_str):
        """Check waitlist with proper client email handling"""
        for entry in self.waitlist:
            if (entry['professional_id'] == professional_id and 
                date_str in entry['preferred_dates']):
                
                # Get client email using ClientManager
                client_email = self.client_manager.get_client_email(entry['client_name'])
                if not client_email:
                    continue  # Skip if no email found
                
                notifier = self.notification_service()
                notifier.notify_waitlist({
                    'client_name': entry['client_name'],
                    'client_email': client_email,
                    'date': date_str,
                    'professional_id': professional_id
                })
