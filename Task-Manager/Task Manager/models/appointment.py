from datetime import datetime

class Appointment:
    def __init__(self, id, client_name, professional_id, service_type, 
                 start_time, duration, status="scheduled", payment_status="pending"):
        self.id = id
        self.client_name = client_name
        self.professional_id = professional_id
        self.service_type = service_type
        self.start_time = start_time
        self.duration = duration
        self.status = status
        self.payment_status = payment_status
        self.deposit_amount = 0
