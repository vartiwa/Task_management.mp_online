# Task Manager

Task Manager is a Python-based command-line application for organizing tasks, scheduling appointments, managing professionals and clients, and sending notifications. It stores data locally in CSV and JSON files, so it can run without a database server.

## Description

The application combines task tracking with appointment scheduling in a single terminal workflow. Users can create and manage tasks with priorities, deadlines, and dependencies, book appointments against professional availability, maintain a waitlist, configure scheduling settings, and export or import stored data for backup purposes.

## Features

- Create, update, remove, and view tasks
- Track task priority, deadline, status, and dependencies
- Visualize task dependencies as a graph
- Schedule appointments against professional availability
- Manage professionals, clients, and waitlists
- Send welcome emails, reminders, and waitlist notifications when email is enabled
- Export and import all data from a backup folder
- View basic analytics for tasks, appointments, and professional workload

## Data Files

The app uses local files in the project root to persist data:

- `tasks.csv` for task records
- `appointments.csv` for appointment records
- `clients.csv` for client records
- `professionals.csv` for professional records
- `dependencies.json` for task dependency edges
- `scheduling_config.json` for scheduling settings
- `notification_config.json` for email notification settings
- `waitlist.json` for waitlist entries

## Requirements

- Python 3.10 or newer
- `pandas`
- `networkx`
- `matplotlib`
- `stripe`

## Setup

1. Create and activate a virtual environment.
2. Install the dependencies:

```bash
pip install pandas networkx matplotlib stripe
```

## Run

Start the application from the project root:

```bash
python main.py
```

## Main Menu

The program opens an interactive menu with these sections:

- Task Management
- Scheduling
- Analytics
- Settings
- Exit

## Notes

- Email notifications are disabled by default until configured in `notification_config.json`.
- If the data files do not exist, the application creates them on first run.
- Backup exports are written to a timestamped `backup_YYYYMMDD_HHMMSS` folder.
