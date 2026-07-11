from datetime import datetime

class Professional:
    def __init__(self, id, name, services, availability, break_times=None, 
                 email=None, phone=None, specialization=None):
        self.id = id
        self.name = name
        self.services = services  # List of services offered
        self.availability = availability  # Weekly schedule
        self.break_times = break_times or []
        self.email = email
        self.phone = phone
        self.specialization = specialization
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        """Convert professional details to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'services': ','.join(self.services),
            'working_hours': self.availability,
            'break_times': ','.join(self.break_times),
            'email': self.email,
            'phone': self.phone,
            'specialization': self.specialization,
            'created_at': self.created_at
        }
