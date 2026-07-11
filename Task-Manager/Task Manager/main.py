import pandas as pd
import os
import json
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from services.scheduler import SchedulingEngine
from services.notification_service import NotificationService
from models.professional import Professional

class TaskManager:
    def __init__(self, file_name="tasks.csv", graph_file="dependencies.json"):
        """
        Initialize the TaskManager with file paths for tasks and dependencies.
        
        :param file_name: Path to the CSV file storing tasks
        :param graph_file: Path to the JSON file storing task dependencies
        """
        self.file_name = file_name
        self.graph_file = graph_file
        
        # Initialize the CSV file if it doesn't exist
        self.initialize_csv()
        
        # Load existing graph or create a new one
        self.graph = self.load_or_create_graph()

        self.scheduler = SchedulingEngine()
        self.notification_service = NotificationService()
        self.professionals_file = "professionals.csv"
        self.initialize_professionals()

    def initialize_csv(self):
        """
        Create the CSV file with the required columns if it doesn't exist.
        """
        if not os.path.exists(self.file_name):
            cols = ["id", "task_name", "category", "priority", "deadline", "dependencies", "status", "created_at"]
            df = pd.DataFrame(columns=cols)
            df.to_csv(self.file_name, index=False)

    def initialize_professionals(self):
        """Initialize professionals CSV file if it doesn't exist"""
        if not os.path.exists(self.professionals_file):
            cols = ["id", "name", "services", "working_hours", "break_times", 
                   "email", "phone", "specialization"]
            pd.DataFrame(columns=cols).to_csv(self.professionals_file, index=False)

    def load_or_create_graph(self):
        """
        Load existing task dependency graph or create a new one.
        
        :return: NetworkX Directed Graph of task dependencies
        """
        try:
            with open(self.graph_file, 'r') as f:
                graph_data = json.load(f)
                graph = nx.DiGraph()
                for edge in graph_data.get('edges', []):
                    graph.add_edge(edge[0], edge[1])
                return graph
        except FileNotFoundError:
            return nx.DiGraph()

    def save_graph(self):
        """
        Save the current task dependency graph to a JSON file.
        """
        graph_data = {
            'edges': list(self.graph.edges())
        }
        with open(self.graph_file, 'w') as f:
            json.dump(graph_data, f)

    def add_task(self):
        """Add a new task with scheduling capabilities"""
        df = pd.read_csv(self.file_name)
        next_id = df['id'].max() + 1 if not df.empty else 1

        print("\n=== Task Details ===")
        name = input("Enter the task name: ").strip()
        if name in df['task_name'].values:
            print("A task with this name already exists.")
            return

        category = input("Enter the task category: ").strip()
        
        while True:
            try:
                priority = int(input("Enter the priority (1-100): "))
                if 1 <= priority <= 100:
                    break
                print("Priority must be between 1 and 100.")
            except ValueError:
                print("Please enter a valid integer.")

        print("\n=== Scheduling Details ===")
        needs_scheduling = input("Does this task require scheduling? (y/n): ").lower() == 'y'

        if needs_scheduling:
            # Get professional details
            prof_df = pd.read_csv(self.professionals_file)
            if prof_df.empty:
                print("\nNo professionals available. Adding new professional...")
                prof_id = self.add_professional()
            else:
                print("\nAvailable Professionals:")
                print(prof_df[['id', 'name', 'services']].to_string())
                prof_id = input("Enter professional ID (or 'new' to add): ").strip()
                if prof_id.lower() == 'new':
                    prof_id = self.add_professional()

            # Get appointment details
            date_str = input("Enter appointment date (YYYY-MM-DD): ").strip()
            available_slots = self.scheduler.check_availability(prof_id, date_str)
            
            if not available_slots:
                print("No available slots for this date.")
                add_to_waitlist = input("Add to waitlist? (y/n): ").lower() == 'y'
                if add_to_waitlist:
                    preferred_dates = [date_str]
                    while input("Add another preferred date? (y/n): ").lower() == 'y':
                        preferred_dates.append(input("Enter date (YYYY-MM-DD): ").strip())
                    self.scheduler.add_to_waitlist(name, prof_id, preferred_dates)
                return

            print("\nAvailable slots:")
            for i, slot in enumerate(available_slots, 1):
                print(f"{i}. {slot}")
            
            while True:
                try:
                    slot_choice = int(input("Choose slot number: ")) - 1
                    time_str = available_slots[slot_choice]
                    break
                except (ValueError, IndexError):
                    print("Invalid choice. Please try again.")

            success, message = self.scheduler.book_appointment(
                name, prof_id, category, date_str, time_str
            )
            if not success:
                print(f"Booking failed: {message}")
                return

        # Handle regular task details
        while True:
            try:
                deadline = int(input("\nEnter the deadline in days: "))
                if deadline > 0:
                    break
                print("Deadline must be a positive number.")
            except ValueError:
                print("Please enter a valid integer.")

        dependencies_input = input("Enter dependencies (comma-separated task names, or press Enter if none): ").strip()
        dependencies = [dep.strip() for dep in dependencies_input.split(',') if dep.strip()] if dependencies_input else []

        invalid_dependencies = [dep for dep in dependencies if dep not in df['task_name'].values]
        if invalid_dependencies:
            print(f"Warning: The following dependencies do not exist: {invalid_dependencies}")
            if input("Continue? (y/n): ").lower() != 'y':
                return

        for dependency in dependencies:
            self.graph.add_edge(dependency, name)

        task_data = pd.DataFrame({
            "id": [next_id],
            "task_name": [name],
            "category": [category],
            "priority": [priority],
            "deadline": [deadline],
            "dependencies": [', '.join(dependencies) if dependencies else 'None'],
            "status": ["Not Started"],
            "created_at": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        })

        df = pd.concat([df, task_data], ignore_index=True)
        df.to_csv(self.file_name, index=False)
        self.save_graph()
        print("Task added successfully!")

    def add_professional(self):
        """Add a new professional to the system"""
        prof_df = pd.read_csv(self.professionals_file)
        next_id = prof_df['id'].max() + 1 if not prof_df.empty else 1

        print("\n=== Add Professional ===")
        name = input("Enter professional name: ").strip()
        services = input("Enter services (comma-separated): ").strip()
        email = input("Enter email: ").strip()
        phone = input("Enter phone: ").strip()
        specialization = input("Enter specialization: ").strip()
        
        print("\nWorking hours (24-hour format)")
        start_hour = input("Start time (e.g., 09:00): ").strip()
        end_hour = input("End time (e.g., 17:00): ").strip()
        working_hours = f"{start_hour}-{end_hour}"

        break_times = input("Enter break times (format: HH:MM-HH:MM, comma-separated): ").strip()

        professional = Professional(
            id=next_id,
            name=name,
            services=services.split(','),
            availability=working_hours,
            break_times=break_times.split(',') if break_times else None,
            email=email,
            phone=phone,
            specialization=specialization
        )

        prof_df = pd.concat([prof_df, pd.DataFrame([professional.to_dict()])], 
                          ignore_index=True)
        prof_df.to_csv(self.professionals_file, index=False)
        print(f"Professional added successfully with ID: {next_id}")
        return next_id

    def remove_task(self):
        """
        Remove a task from the task management system.
        """
        # Read current tasks
        df = pd.read_csv(self.file_name)
        
        # Display current tasks
        print("\nCurrent Tasks:")
        print(df.to_string(index=False))
        
        # Get task name to remove
        name = input("\nEnter the name of the task to remove: ").strip()
        
        # Check if task exists
        if name not in df['task_name'].values:
            print(f"Task '{name}' not found in the list.")
            return
        
        # Remove task from DataFrame
        df = df[df['task_name'] != name]
        df.to_csv(self.file_name, index=False)
        
        # Remove task from graph
        if name in self.graph:
            self.graph.remove_node(name)
        self.save_graph()
        
        print(f"Task '{name}' has been removed successfully.")
        
        # Display updated tasks
        print("\nUpdated Tasks:")
        print(df.to_string(index=False))

    def update_task_status(self):
        """
        Update the status of a specific task.
        """
        df = pd.read_csv(self.file_name)
        
        # Display current tasks
        print("\nCurrent Tasks:")
        print(df.to_string(index=False))
        
        # Select task to update
        name = input("\nEnter the name of the task to update: ").strip()
        
        # Check if task exists
        if name not in df['task_name'].values:
            print(f"Task '{name}' not found in the list.")
            return
        
        # Status selection menu
        print("\nSelect new status:")
        print("1. Not Started")
        print("2. In Progress")
        print("3. Completed")
        
        status_choice = input("Enter your choice (1-3): ").strip()
        status_map = {
            '1': "Not Started",
            '2': "In Progress",
            '3': "Completed"
        }
        
        if status_choice not in status_map:
            print("Invalid choice. Status not updated.")
            return
        
        # Update status in DataFrame
        df.loc[df['task_name'] == name, 'status'] = status_map[status_choice]
        df.to_csv(self.file_name, index=False)
        
        print(f"Status of task '{name}' updated to {status_map[status_choice]}.")

    def view_tasks(self):
        """
        View tasks with optional filtering.
        """
        df = pd.read_csv(self.file_name)
        
        # Filtering options menu
        print("\nView Tasks:")
        print("1. View All Tasks")
        print("2. Filter by Category")
        print("3. Filter by Priority")
        print("4. Filter by Status")
        
        # Take user choice
        choice = input("Enter your choice (1-4): ").strip()
        
        # Different view options based on user choice
        if choice == '1':
            print(df.to_string(index=False))
        elif choice == '2':
            category = input("Enter category to filter: ").strip()
            filtered_df = df[df['category'].str.contains(category, case=False)]
            print(filtered_df.to_string(index=False) if not filtered_df.empty else "No tasks found.")
        elif choice == '3':
            while True:
                try:
                    min_priority = int(input("Enter minimum priority: "))
                    filtered_df = df[df['priority'] >= min_priority]
                    print(filtered_df.to_string(index=False) if not filtered_df.empty else "No tasks found.")
                    break
                except ValueError:
                    print("Please enter a valid integer.")
        elif choice == '4':
            status = input("Enter status to filter (Not Started/In Progress/Completed): ").strip()
            filtered_df = df[df['status'] == status]
            print(filtered_df.to_string(index=False) if not filtered_df.empty else "No tasks found.")
        else:
            print("Invalid choice.")

    def view_overdue_tasks(self):
        """
        View tasks that are past their deadline.
        """
        df = pd.read_csv(self.file_name)
        
        # Get current date
        current_date = datetime.now()
        
        # Calculate overdue tasks
        df['deadline_date'] = pd.to_datetime(current_date) - pd.to_timedelta(df['deadline'], unit='D')
        overdue_tasks = df[df['deadline_date'] > current_date]
        
        if overdue_tasks.empty:
            print("No overdue tasks!")
        else:
            print("\nOverdue Tasks:")
            print(overdue_tasks.to_string(index=False))

    def visualize_dependencies(self):
        """
        Create a visual representation of task dependencies.
        """
        if not self.graph.nodes():
            print("No dependencies to visualize.")
            return
        
        # Create a matplotlib figure
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(self.graph)
        nx.draw(self.graph, pos, with_labels=True, 
                node_color='lightblue', 
                node_size=3000, 
                font_size=10, 
                font_weight='bold', 
                arrows=True)
        plt.title("Task Dependencies")
        plt.show()

    def export_tasks(self):
        """
        Export tasks to a CSV file.
        """
        export_file = input("Enter the export file name (e.g., tasks_backup.csv): ").strip()
        
        df = pd.read_csv(self.file_name)
        df.to_csv(export_file, index=False)
        
        print(f"Tasks exported to {export_file} successfully!")

    def view_analytics(self):
        """Display analytics for appointments and tasks"""
        appointments_df = pd.read_csv(self.scheduler.schedule_file)
        tasks_df = pd.read_csv(self.file_name)
        
        print("\n=== Analytics Dashboard ===")
        
        # Task Statistics
        print("\nTask Statistics:")
        print(f"Total Tasks: {len(tasks_df)}")
        print(f"Completed Tasks: {len(tasks_df[tasks_df['status'] == 'Completed'])}")
        print(f"Overdue Tasks: {len(tasks_df[pd.to_datetime(tasks_df['deadline_date']) < datetime.now()])}")
        
        # Category Analysis
        print("\nTasks by Category:")
        category_counts = tasks_df['category'].value_counts()
        for category, count in category_counts.items():
            print(f"{category}: {count}")
        
        # Appointment Statistics
        if not appointments_df.empty:
            print("\nAppointment Statistics:")
            print(f"Total Appointments: {len(appointments_df)}")
            print(f"Scheduled: {len(appointments_df[appointments_df['status'] == 'scheduled'])}")
            print(f"Completed: {len(appointments_df[appointments_df['status'] == 'completed'])}")
            
            # Professional Workload
            print("\nProfessional Workload:")
            prof_workload = appointments_df['professional_id'].value_counts()
            for prof_id, count in prof_workload.items():
                print(f"Professional {prof_id}: {count} appointments")

    def manage_waitlist(self):
        """View and manage waitlist entries"""
        if not self.scheduler.waitlist:
            print("Waitlist is empty.")
            return
            
        print("\nCurrent Waitlist:")
        for i, entry in enumerate(self.scheduler.waitlist, 1):
            print(f"\n{i}. Client: {entry['client_name']}")
            print(f"   Professional: {entry['professional_id']}")
            print(f"   Preferred Dates: {', '.join(entry['preferred_dates'])}")
            print(f"   Added on: {entry['added_on']}")
        
        if input("\nRemove entries? (y/n): ").lower() == 'y':
            while True:
                try:
                    entry_num = int(input("Enter entry number to remove (0 to finish): "))
                    if entry_num == 0:
                        break
                    if 1 <= entry_num <= len(self.scheduler.waitlist):
                        self.scheduler.waitlist.pop(entry_num - 1)
                        self.scheduler.save_waitlist()
                        print("Entry removed successfully.")
                    else:
                        print("Invalid entry number.")
                except ValueError:
                    print("Please enter a valid number.")

    def scheduling_menu(self):
        """Enhanced scheduling menu"""
        while True:
            print("\n=== Scheduling Menu ===")
            print("1. View Available Slots")
            print("2. Book Appointment")
            print("3. Manage Waitlist")
            print("4. View Analytics")
            print("5. Manage Professionals")
            print("6. Configure Schedule Settings")
            print("7. Back to Main Menu")
            
            choice = input("Enter your choice (1-7): ").strip()
            
            try:
                if choice == '1':
                    self.view_available_slots()
                elif choice == '2':
                    self.book_new_appointment()
                elif choice == '3':
                    self.manage_waitlist()
                elif choice == '4':
                    self.view_analytics()
                elif choice == '5':
                    self.manage_professionals()
                elif choice == '6':
                    self.configure_schedule_settings()
                elif choice == '7':
                    break
                else:
                    print("Invalid choice.")
            except Exception as e:
                print(f"An error occurred: {e}")
                input("Press Enter to continue...")

    def view_available_slots(self):
        """View available slots for a professional"""
        prof_df = pd.read_csv(self.professionals_file)
        if prof_df.empty:
            print("No professionals available.")
            return

        print("\nAvailable Professionals:")
        print(prof_df[['id', 'name', 'services']].to_string())
        prof_id = input("Enter professional ID: ")
        date = input("Enter date (YYYY-MM-DD): ")
        
        slots = self.scheduler.check_availability(prof_id, date)
        if slots:
            print("\nAvailable slots:")
            for i, slot in enumerate(slots, 1):
                print(f"{i}. {slot}")
        else:
            print("No available slots for this date.")

    def main_menu(self):
        """Updated main menu"""
        while True:
            print("\n=== Task Management System ===")
            print("1. Task Management")
            print("2. Scheduling")
            print("3. Analytics")
            print("4. Settings")
            print("5. Exit")
            
            choice = input("Enter your choice (1-5): ").strip()
            
            try:
                if choice == '1':
                    self.task_management_menu()
                elif choice == '2':
                    self.scheduling_menu()
                elif choice == '3':
                    self.analytics_menu()
                elif choice == '4':
                    self.settings_menu()
                elif choice == '5':
                    print("Goodbye!")
                    break
                else:
                    print("Invalid choice.")
            except Exception as e:
                print(f"An error occurred: {e}")
                input("Press Enter to continue...")

    def task_management_menu(self):
        """Separate menu for task management"""
        while True:
            print("\n=== Task Management ===")
            print("1. Add Task")
            print("2. Remove Task")
            print("3. Update Task Status")
            print("4. View Tasks")
            print("5. View Overdue Tasks")
            print("6. Visualize Dependencies")
            print("7. Export Tasks")
            print("8. Back to Main Menu")
            
            choice = input("Enter your choice (1-8): ").strip()
            
            try:
                if choice == '1':
                    self.add_task()
                elif choice == '2':
                    self.remove_task()
                elif choice == '3':
                    self.update_task_status()
                elif choice == '4':
                    self.view_tasks()
                elif choice == '5':
                    self.view_overdue_tasks()
                elif choice == '6':
                    self.visualize_dependencies()
                elif choice == '7':
                    self.export_tasks()
                elif choice == '8':
                    break
                else:
                    print("Invalid choice.")
            except Exception as e:
                print(f"An error occurred: {e}")
                input("Press Enter to continue...")

    def analytics_menu(self):
        """Analytics menu implementation"""
        while True:
            print("\n=== Analytics Dashboard ===")
            print("1. Task Statistics")
            print("2. Appointment Analytics")
            print("3. Professional Workload")
            print("4. Category Analysis")
            print("5. Back to Main Menu")
            
            choice = input("Enter your choice (1-5): ").strip()
            
            try:
                if choice == '1':
                    self.view_task_statistics()
                elif choice == '2':
                    self.view_appointment_analytics()
                elif choice == '3':
                    self.view_professional_workload()
                elif choice == '4':
                    self.view_category_analysis()
                elif choice == '5':
                    break
                else:
                    print("Invalid choice.")
            except Exception as e:
                print(f"An error occurred: {e}")
                input("Press Enter to continue...")

    def settings_menu(self):
        """Settings menu implementation"""
        while True:
            print("\n=== Settings ===")
            print("1. Configure Schedule Settings")
            print("2. Configure Notifications")
            print("3. Manage Professionals")
            print("4. Export/Import Data")
            print("5. Back to Main Menu")
            
            choice = input("Enter your choice (1-5): ").strip()
            
            try:
                if choice == '1':
                    self.configure_schedule_settings()
                elif choice == '2':
                    self.configure_notifications()
                elif choice == '3':
                    self.manage_professionals()
                elif choice == '4':
                    self.manage_data()
                elif choice == '5':
                    break
                else:
                    print("Invalid choice.")
            except Exception as e:
                print(f"An error occurred: {e}")
                input("Press Enter to continue...")

    def configure_schedule_settings(self):
        """Configure scheduling settings"""
        print("\n=== Schedule Settings ===")
        print("Current settings:")
        config = self.scheduler.load_config()
        print(f"Working hours: {config['working_hours']['start']}:00 - {config['working_hours']['end']}:00")
        print(f"Slot duration: {config['slot_duration']} minutes")
        
        if input("\nUpdate settings? (y/n): ").lower() == 'y':
            try:
                start = int(input("Enter working hours start (24-hour format, e.g., 9): "))
                end = int(input("Enter working hours end (24-hour format, e.g., 17): "))
                duration = int(input("Enter slot duration in minutes: "))
                
                new_config = {
                    'working_hours': {'start': start, 'end': end},
                    'slot_duration': duration
                }
                self.scheduler.update_config(new_config)
                print("Settings updated successfully!")
            except ValueError:
                print("Invalid input. Settings not updated.")

    def configure_notifications(self):
        """Configure notification settings"""
        print("\n=== Notification Settings ===")
        config = self.notification_service.config
        print("Current settings:")
        print(f"Email notifications: {'Enabled' if config['email_enabled'] else 'Disabled'}")
        
        if input("\nConfigure email notifications? (y/n): ").lower() == 'y':
            config['email_enabled'] = input("Enable email notifications? (y/n): ").lower() == 'y'
            if config['email_enabled']:
                config['smtp_server'] = input("Enter SMTP server: ")
                config['smtp_port'] = int(input("Enter SMTP port: "))
                config['smtp_username'] = input("Enter SMTP username: ")
                config['smtp_password'] = input("Enter SMTP password: ")
                config['from_email'] = input("Enter sender email: ")
            
            with open(self.notification_service.config_file, 'w') as f:
                json.dump(config, f)
            print("Notification settings updated successfully!")

    def manage_professionals(self):
        """Manage professionals"""
        while True:
            print("\n=== Manage Professionals ===")
            print("1. View All Professionals")
            print("2. Add Professional")
            print("3. Update Professional")
            print("4. Remove Professional")
            print("5. Back")
            
            choice = input("Enter your choice (1-5): ").strip()
            
            try:
                if choice == '1':
                    prof_df = pd.read_csv(self.professionals_file)
                    if prof_df.empty:
                        print("No professionals found.")
                    else:
                        print("\nProfessionals:")
                        print(prof_df.to_string(index=False))
                elif choice == '2':
                    self.add_professional()
                elif choice == '3':
                    self.update_professional()
                elif choice == '4':
                    self.remove_professional()
                elif choice == '5':
                    break
                else:
                    print("Invalid choice.")
            except Exception as e:
                print(f"An error occurred: {e}")
                input("Press Enter to continue...")

    def update_professional(self):
        """Update professional details"""
        prof_df = pd.read_csv(self.professionals_file)
        if prof_df.empty:
            print("No professionals found.")
            return
            
        print("\nCurrent Professionals:")
        print(prof_df[['id', 'name', 'services']].to_string())
        
        prof_id = input("\nEnter professional ID to update: ")
        if not prof_df[prof_df['id'] == int(prof_id)].empty:
            print("\nUpdate fields (press Enter to skip):")
            row_idx = prof_df[prof_df['id'] == int(prof_id)].index[0]
            
            name = input("Name: ").strip() or prof_df.at[row_idx, 'name']
            services = input("Services (comma-separated): ").strip() or prof_df.at[row_idx, 'services']
            working_hours = input("Working hours (HH:MM-HH:MM): ").strip() or prof_df.at[row_idx, 'working_hours']
            break_times = input("Break times: ").strip() or prof_df.at[row_idx, 'break_times']
            
            prof_df.at[row_idx, 'name'] = name
            prof_df.at[row_idx, 'services'] = services
            prof_df.at[row_idx, 'working_hours'] = working_hours
            prof_df.at[row_idx, 'break_times'] = break_times
            
            prof_df.to_csv(self.professionals_file, index=False)
            print("Professional updated successfully!")
        else:
            print("Professional not found.")

    def remove_professional(self):
        """Remove a professional"""
        prof_df = pd.read_csv(self.professionals_file)
        if prof_df.empty:
            print("No professionals found.")
            return
            
        print("\nCurrent Professionals:")
        print(prof_df[['id', 'name', 'services']].to_string())
        
        prof_id = input("\nEnter professional ID to remove: ")
        if not prof_df[prof_df['id'] == int(prof_id)].empty:
            prof_df = prof_df[prof_df['id'] != int(prof_id)]
            prof_df.to_csv(self.professionals_file, index=False)
            print("Professional removed successfully!")
        else:
            print("Professional not found.")

    def manage_data(self):
        """Manage data export/import"""
        while True:
            print("\n=== Data Management ===")
            print("1. Export All Data")
            print("2. Import Data")
            print("3. Back")
            
            choice = input("Enter your choice (1-3): ").strip()
            
            try:
                if choice == '1':
                    self.export_all_data()
                elif choice == '2':
                    self.import_data()
                elif choice == '3':
                    break
                else:
                    print("Invalid choice.")
            except Exception as e:
                print(f"An error occurred: {e}")
                input("Press Enter to continue...")

    def export_all_data(self):
        """Export all data to a backup folder"""
        backup_dir = "backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Copy all data files to backup directory
        files_to_backup = [
            self.file_name,
            self.graph_file,
            self.professionals_file,
            self.scheduler.schedule_file,
            self.scheduler.config_file,
            self.notification_service.config_file
        ]
        
        for file in files_to_backup:
            if os.path.exists(file):
                import shutil
                shutil.copy2(file, os.path.join(backup_dir, os.path.basename(file)))
        
        print(f"All data exported to {backup_dir} successfully!")

    def import_data(self):
        """Import data from backup"""
        backup_dir = input("Enter backup directory path: ")
        if not os.path.exists(backup_dir):
            print("Backup directory not found.")
            return
            
        try:
            # Copy files from backup to current directory
            for file in os.listdir(backup_dir):
                import shutil
                shutil.copy2(os.path.join(backup_dir, file), file)
            print("Data imported successfully!")
        except Exception as e:
            print(f"Error importing data: {e}")

if __name__ == "__main__":
    task_manager = TaskManager()
    task_manager.main_menu()