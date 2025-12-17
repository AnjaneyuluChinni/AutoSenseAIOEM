import sqlite3
import json
from datetime import datetime, timedelta
import random
from contextlib import contextmanager

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "autosenseai.db")

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(
    DATABASE_PATH,
    check_same_thread=False
)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vin TEXT UNIQUE NOT NULL,
                make TEXT NOT NULL,
                model TEXT NOT NULL,
                year INTEGER NOT NULL,
                owner_name TEXT NOT NULL,
                owner_email TEXT,
                owner_phone TEXT,
                mileage INTEGER DEFAULT 0,
                last_service_date TEXT,
                health_score REAL DEFAULT 100.0,
                status TEXT DEFAULT 'healthy',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telemetry_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                engine_temp REAL,
                oil_pressure REAL,
                battery_voltage REAL,
                rpm INTEGER,
                speed INTEGER,
                vibration_level REAL,
                brake_wear REAL,
                tire_pressure_fl REAL,
                tire_pressure_fr REAL,
                tire_pressure_rl REAL,
                tire_pressure_rr REAL,
                error_codes TEXT,
                fuel_level REAL,
                coolant_temp REAL,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                component TEXT NOT NULL,
                description TEXT,
                failure_probability REAL,
                predicted_failure_date TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS service_centers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT NOT NULL,
                capacity INTEGER DEFAULT 10,
                current_load INTEGER DEFAULT 0,
                specializations TEXT,
                rating REAL DEFAULT 4.0,
                contact_phone TEXT,
                operating_hours TEXT DEFAULT '9:00-18:00'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                service_center_id INTEGER NOT NULL,
                alert_id INTEGER,
                booking_date TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                service_type TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                estimated_duration INTEGER DEFAULT 60,
                status TEXT DEFAULT 'scheduled',
                customer_confirmed INTEGER DEFAULT 0,
                technician_notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                FOREIGN KEY (service_center_id) REFERENCES service_centers(id),
                FOREIGN KEY (alert_id) REFERENCES alerts(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                vehicle_id INTEGER NOT NULL,
                rating INTEGER,
                comments TEXT,
                issue_resolved INTEGER DEFAULT 1,
                additional_issues TEXT,
                rca_notes TEXT,
                capa_actions TEXT,
                oem_notified INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings(id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL,
                action TEXT NOT NULL,
                input_data TEXT,
                output_data TEXT,
                decision_reasoning TEXT,
                execution_time REAL,
                status TEXT DEFAULT 'success',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rca_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component TEXT NOT NULL,
                failure_pattern TEXT,
                root_cause TEXT,
                affected_vehicles INTEGER DEFAULT 0,
                severity TEXT,
                recommendation TEXT,
                oem_action_required INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()

def seed_sample_data():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        if cursor.fetchone()[0] > 0:
            return
        
        vehicles = [
            ("VIN001HERO2024A", "Hero", "Splendor Plus", 2024, "Rahul Sharma", "rahul@email.com", "9876543210", 15000, "2024-10-15"),
            ("VIN002HERO2023B", "Hero", "Xtreme 160R", 2023, "Priya Patel", "priya@email.com", "9876543211", 25000, "2024-09-20"),
            ("VIN003MAH2024C", "Mahindra", "Thar", 2024, "Amit Kumar", "amit@email.com", "9876543212", 18000, "2024-11-01"),
            ("VIN004MAH2023D", "Mahindra", "XUV700", 2023, "Sneha Reddy", "sneha@email.com", "9876543213", 35000, "2024-08-15"),
            ("VIN005HERO2022E", "Hero", "Passion Pro", 2022, "Vikram Singh", "vikram@email.com", "9876543214", 45000, "2024-07-10"),
            ("VIN006MAH2024F", "Mahindra", "Scorpio-N", 2024, "Anita Desai", "anita@email.com", "9876543215", 12000, "2024-11-20"),
            ("VIN007HERO2023G", "Hero", "Glamour", 2023, "Rajesh Iyer", "rajesh@email.com", "9876543216", 28000, "2024-10-05"),
            ("VIN008MAH2022H", "Mahindra", "Bolero", 2022, "Kavita Menon", "kavita@email.com", "9876543217", 55000, "2024-06-25"),
            ("VIN009HERO2024I", "Hero", "Xpulse 200", 2024, "Deepak Joshi", "deepak@email.com", "9876543218", 8000, "2024-12-01"),
            ("VIN010MAH2023J", "Mahindra", "XUV300", 2023, "Meera Nair", "meera@email.com", "9876543219", 22000, "2024-09-15"),
        ]
        
        cursor.executemany('''
            INSERT INTO vehicles (vin, make, model, year, owner_name, owner_email, owner_phone, mileage, last_service_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', vehicles)
        
        service_centers = [
            ("Hero Service Hub - Central", "Mumbai Central", 15, 3, '["two-wheeler", "engine", "electrical"]', 4.5, "022-12345678", "8:00-20:00"),
            ("Mahindra Authorized - Andheri", "Andheri West", 20, 5, '["SUV", "engine", "transmission", "body"]', 4.3, "022-23456789", "9:00-19:00"),
            ("Hero Express Service", "Thane", 10, 2, '["two-wheeler", "quick-service"]', 4.7, "022-34567890", "8:00-21:00"),
            ("Mahindra Premium Care", "Powai", 25, 8, '["SUV", "premium", "full-service"]', 4.8, "022-45678901", "9:00-18:00"),
            ("Multi-brand Service Center", "Navi Mumbai", 30, 10, '["all", "general"]', 4.0, "022-56789012", "7:00-22:00"),
        ]
        
        cursor.executemany('''
            INSERT INTO service_centers (name, location, capacity, current_load, specializations, rating, contact_phone, operating_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', service_centers)
        
        conn.commit()

def get_all_vehicles():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_vehicle_by_id(vehicle_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_alerts(status=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute('''
                SELECT a.*, v.vin, v.make, v.model, v.owner_name 
                FROM alerts a 
                JOIN vehicles v ON a.vehicle_id = v.id 
                WHERE a.status = ?
                ORDER BY a.created_at DESC
            ''', (status,))
        else:
            cursor.execute('''
                SELECT a.*, v.vin, v.make, v.model, v.owner_name 
                FROM alerts a 
                JOIN vehicles v ON a.vehicle_id = v.id 
                ORDER BY a.created_at DESC
            ''')
        return [dict(row) for row in cursor.fetchall()]

def create_alert(vehicle_id, alert_type, severity, component, description, failure_probability, predicted_failure_date=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alerts (vehicle_id, alert_type, severity, component, description, failure_probability, predicted_failure_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (vehicle_id, alert_type, severity, component, description, failure_probability, predicted_failure_date))
        conn.commit()
        return cursor.lastrowid

def get_all_service_centers():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM service_centers ORDER BY rating DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_all_bookings(status=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute('''
                SELECT b.*, v.vin, v.make, v.model, v.owner_name, v.owner_phone,
                       sc.name as service_center_name, sc.location as service_center_location
                FROM bookings b
                JOIN vehicles v ON b.vehicle_id = v.id
                JOIN service_centers sc ON b.service_center_id = sc.id
                WHERE b.status = ?
                ORDER BY b.booking_date, b.booking_time
            ''', (status,))
        else:
            cursor.execute('''
                SELECT b.*, v.vin, v.make, v.model, v.owner_name, v.owner_phone,
                       sc.name as service_center_name, sc.location as service_center_location
                FROM bookings b
                JOIN vehicles v ON b.vehicle_id = v.id
                JOIN service_centers sc ON b.service_center_id = sc.id
                ORDER BY b.booking_date DESC, b.booking_time
            ''')
        return [dict(row) for row in cursor.fetchall()]

def create_booking(vehicle_id, service_center_id, alert_id, booking_date, booking_time, service_type, priority, estimated_duration):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bookings (vehicle_id, service_center_id, alert_id, booking_date, booking_time, service_type, priority, estimated_duration)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (vehicle_id, service_center_id, alert_id, booking_date, booking_time, service_type, priority, estimated_duration))
        conn.commit()
        return cursor.lastrowid

def update_booking_status(booking_id, status, notes=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if status == 'completed':
            cursor.execute('''
                UPDATE bookings SET status = ?, technician_notes = ?, completed_at = ?
                WHERE id = ?
            ''', (status, notes, datetime.now().isoformat(), booking_id))
        else:
            cursor.execute('''
                UPDATE bookings SET status = ?, technician_notes = ?
                WHERE id = ?
            ''', (status, notes, booking_id))
        conn.commit()

def create_feedback(booking_id, vehicle_id, rating, comments, issue_resolved, additional_issues, rca_notes, capa_actions):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (booking_id, vehicle_id, rating, comments, issue_resolved, additional_issues, rca_notes, capa_actions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (booking_id, vehicle_id, rating, comments, issue_resolved, additional_issues, rca_notes, capa_actions))
        conn.commit()
        return cursor.lastrowid

def get_all_feedback():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.*, v.vin, v.make, v.model, b.service_type, sc.name as service_center_name
            FROM feedback f
            JOIN vehicles v ON f.vehicle_id = v.id
            JOIN bookings b ON f.booking_id = b.id
            JOIN service_centers sc ON b.service_center_id = sc.id
            ORDER BY f.created_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

def log_agent_action(agent_name, action, input_data, output_data, decision_reasoning, execution_time, status='success'):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO agent_logs (agent_name, action, input_data, output_data, decision_reasoning, execution_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (agent_name, action, json.dumps(input_data) if input_data else None, 
              json.dumps(output_data) if output_data else None, decision_reasoning, execution_time, status))
        conn.commit()
        return cursor.lastrowid

def get_agent_logs(limit=50):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]

def save_telemetry(vehicle_id, telemetry):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO telemetry_data (
                vehicle_id, timestamp, engine_temp, oil_pressure, battery_voltage,
                rpm, speed, vibration_level, brake_wear, tire_pressure_fl,
                tire_pressure_fr, tire_pressure_rl, tire_pressure_rr, error_codes,
                fuel_level, coolant_temp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vehicle_id, telemetry['timestamp'], telemetry['engine_temp'],
            telemetry['oil_pressure'], telemetry['battery_voltage'], telemetry['rpm'],
            telemetry['speed'], telemetry['vibration_level'], telemetry['brake_wear'],
            telemetry['tire_pressure_fl'], telemetry['tire_pressure_fr'],
            telemetry['tire_pressure_rl'], telemetry['tire_pressure_rr'],
            json.dumps(telemetry.get('error_codes', [])), telemetry['fuel_level'],
            telemetry['coolant_temp']
        ))
        conn.commit()

def get_telemetry_history(vehicle_id, limit=100):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM telemetry_data WHERE vehicle_id = ?
            ORDER BY timestamp DESC LIMIT ?
        ''', (vehicle_id, limit))
        return [dict(row) for row in cursor.fetchall()]

def update_vehicle_health(vehicle_id, health_score, status):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE vehicles SET health_score = ?, status = ?
            WHERE id = ?
        ''', (health_score, status, vehicle_id))
        conn.commit()

def create_rca_report(component, failure_pattern, root_cause, affected_vehicles, severity, recommendation, oem_action_required):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO rca_reports (component, failure_pattern, root_cause, affected_vehicles, severity, recommendation, oem_action_required)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (component, failure_pattern, root_cause, affected_vehicles, severity, recommendation, oem_action_required))
        conn.commit()
        return cursor.lastrowid

def get_rca_reports():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rca_reports ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_dashboard_stats():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'active'")
        active_alerts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'scheduled'")
        pending_bookings = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bookings WHERE status = 'completed'")
        completed_services = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(rating) FROM feedback")
        avg_rating = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE status = 'critical'")
        critical_vehicles = cursor.fetchone()[0]
        
        return {
            'total_vehicles': total_vehicles,
            'active_alerts': active_alerts,
            'pending_bookings': pending_bookings,
            'completed_services': completed_services,
            'avg_rating': round(avg_rating, 1),
            'critical_vehicles': critical_vehicles
        }
