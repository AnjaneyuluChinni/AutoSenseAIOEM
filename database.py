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
        cursor = conn.cursor()# Add these tables to init_database() function in database.py

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS garages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                address TEXT NOT NULL,
                phone TEXT,
                rating REAL DEFAULT 3.0,
                specialization TEXT,
                estimated_response_time INTEGER DEFAULT 30,
                capacity INTEGER DEFAULT 5,
                current_load INTEGER DEFAULT 0,
                operating_hours TEXT DEFAULT '24/7',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_number TEXT UNIQUE NOT NULL,
                part_name TEXT NOT NULL,
                category TEXT NOT NULL,
                make TEXT,
                model TEXT,
                year_from INTEGER,
                year_to INTEGER,
                oem_price REAL NOT NULL,
                aftermarket_price REAL,
                stock_quantity INTEGER DEFAULT 0,
                lead_time_days INTEGER DEFAULT 3,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS breakdown_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                garage_id INTEGER,
                breakdown_type TEXT NOT NULL,
                breakdown_location_lat REAL,
                breakdown_location_lng REAL,
                reported_at TEXT DEFAULT CURRENT_TIMESTAMP,
                estimated_fix_time INTEGER,
                actual_fix_time INTEGER,
                status TEXT DEFAULT 'reported',
                parts_used TEXT,
                total_cost REAL,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                FOREIGN KEY (garage_id) REFERENCES garages(id)
            )
        ''')

        # In the init_database() function in database.py, update the breakdown_incidents table creation:
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS breakdown_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_id INTEGER NOT NULL,
                garage_id INTEGER,
                breakdown_type TEXT NOT NULL,
                breakdown_location_lat REAL,
                breakdown_location_lng REAL,
                reported_at TEXT DEFAULT CURRENT_TIMESTAMP,
                estimated_fix_time INTEGER,
                actual_fix_time INTEGER,
                status TEXT DEFAULT 'reported',
                parts_used TEXT,
                total_cost REAL,
                technician_notes TEXT,  -- ADD THIS LINE
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,  -- ADD THIS LINE
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                FOREIGN KEY (garage_id) REFERENCES garages(id)
            )
        ''')
        
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
# Add this function to database.py
def seed_additional_data():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if garages already exist
        cursor.execute("SELECT COUNT(*) FROM garages")
        if cursor.fetchone()[0] == 0:
            garages = [
                ("QuickFix Auto Services", 19.0760, 72.8777, "Mumbai Central", "022-11111111", 4.2, "Emergency, General", 15, 10, 3),
                ("Hero Roadside Assistance", 19.2183, 72.9781, "Thane", "022-22222222", 4.5, "Hero, Two-Wheelers", 20, 8, 2),
                ("Mahindra On-Site Repair", 19.1077, 72.8482, "Andheri", "022-33333333", 4.3, "Mahindra, SUV", 25, 12, 4),
                ("24x7 Emergency Garage", 19.0176, 72.8561, "South Mumbai", "022-44444444", 3.8, "All Brands", 10, 15, 6),
                ("Premium Auto Care", 19.1364, 72.8296, "Bandra", "022-55555555", 4.7, "Premium, Electrical", 30, 6, 1),
                ("Express Mobile Mechanics", 19.0790, 72.9080, "Goregaon", "022-66666666", 4.0, "Mobile, Quick", 15, 5, 2),
            ]
            
            cursor.executemany('''
                INSERT INTO garages (name, latitude, longitude, address, phone, rating, specialization, 
                                   estimated_response_time, capacity, current_load)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', garages)
        
        # Check if parts already exist
        cursor.execute("SELECT COUNT(*) FROM parts_catalog")
        if cursor.fetchone()[0] == 0:
            parts = [
                ("ENG001", "Engine Assembly", "Engine", "Hero", "Splendor", 2020, 2024, 15000.00, 12000.00, 5, 7),
                ("BAT001", "Battery 12V", "Electrical", "Hero", "All Models", 2018, 2024, 3000.00, 2500.00, 20, 2),
                ("BRA001", "Brake Pad Set", "Brakes", "Hero", "All Models", 2018, 2024, 1200.00, 900.00, 50, 1),
                ("TIR001", "Tire (Front)", "Tires", "Hero", "Splendor", 2020, 2024, 1800.00, 1500.00, 30, 3),
                ("ENG002", "Engine Assembly", "Engine", "Mahindra", "Thar", 2020, 2024, 45000.00, 38000.00, 3, 14),
                ("BAT002", "Battery 12V", "Electrical", "Mahindra", "Thar", 2020, 2024, 4500.00, 3800.00, 15, 3),
                ("SUS001", "Suspension Kit", "Suspension", "Mahindra", "XUV700", 2022, 2024, 25000.00, 21000.00, 4, 10),
                ("ALT001", "Alternator", "Electrical", "Mahindra", "All Models", 2020, 2024, 8000.00, 6500.00, 8, 5),
                ("RAD001", "Radiator", "Cooling", "Both", "All Models", 2018, 2024, 5000.00, 4200.00, 12, 4),
                ("OIL001", "Oil Filter", "Engine", "Both", "All Models", 2018, 2024, 500.00, 350.00, 100, 1),
            ]
            
            cursor.executemany('''
                INSERT INTO parts_catalog (part_number, part_name, category, make, model, 
                                         year_from, year_to, oem_price, aftermarket_price, 
                                         stock_quantity, lead_time_days)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', parts)
        
        conn.commit()
def get_all_vehicles():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
# Add these functions to database.py

def get_nearby_garages(latitude, longitude, radius_km=10):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT *, 
            (6371 * acos(
                cos(radians(?)) * cos(radians(latitude)) * 
                cos(radians(longitude) - radians(?)) + 
                sin(radians(?)) * sin(radians(latitude))
            )) as distance_km
            FROM garages
            WHERE distance_km < ?
            ORDER BY distance_km, rating DESC
        ''', (latitude, longitude, latitude, radius_km))
        return [dict(row) for row in cursor.fetchall()]

def get_parts_catalog(make=None, model=None, category=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM parts_catalog WHERE 1=1"
        params = []
        
        if make:
            query += " AND (make = ? OR make = 'Both')"
            params.append(make)
        if model:
            query += " AND (model = ? OR model = 'All Models')"
            params.append(model)
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY part_name"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def create_breakdown_incident(vehicle_id, breakdown_type, latitude, longitude, garage_id=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO breakdown_incidents (vehicle_id, breakdown_type, 
                                           breakdown_location_lat, breakdown_location_lng,
                                           garage_id, reported_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (vehicle_id, breakdown_type, latitude, longitude, garage_id, 
              datetime.now().isoformat(), 'reported'))
        conn.commit()
        return cursor.lastrowid

def update_breakdown_estimate(incident_id, estimated_fix_time, garage_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE breakdown_incidents 
            SET estimated_fix_time = ?, garage_id = ?, status = 'assigned'
            WHERE id = ?
        ''', (estimated_fix_time, garage_id, incident_id))
        conn.commit()

def get_breakdown_history(vehicle_id=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if vehicle_id:
            cursor.execute('''
                SELECT b.*, v.make, v.model, v.vin, g.name as garage_name
                FROM breakdown_incidents b
                JOIN vehicles v ON b.vehicle_id = v.id
                LEFT JOIN garages g ON b.garage_id = g.id
                WHERE b.vehicle_id = ?
                ORDER BY b.reported_at DESC
            ''', (vehicle_id,))
        else:
            cursor.execute('''
                SELECT b.*, v.make, v.model, v.vin, g.name as garage_name
                FROM breakdown_incidents b
                JOIN vehicles v ON b.vehicle_id = v.id
                LEFT JOIN garages g ON b.garage_id = g.id
                ORDER BY b.reported_at DESC
            ''')
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

def get_vehicles_by_status(status):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE status = ? ORDER BY health_score", (status,))
        return [dict(row) for row in cursor.fetchall()]

def get_vehicles_by_make(make):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE make = ? ORDER BY year DESC", (make,))
        return [dict(row) for row in cursor.fetchall()]
    
def update_alert_status(alert_id, status, resolved_at=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if resolved_at:
            cursor.execute('''
                UPDATE alerts SET status = ?, resolved_at = ? WHERE id = ?
            ''', (status, resolved_at, alert_id))
        else:
            cursor.execute('''
                UPDATE alerts SET status = ? WHERE id = ?
            ''', (status, alert_id))
        conn.commit()

def get_alerts_by_vehicle(vehicle_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, v.vin, v.make, v.model 
            FROM alerts a 
            JOIN vehicles v ON a.vehicle_id = v.id 
            WHERE a.vehicle_id = ?
            ORDER BY a.severity DESC, a.created_at DESC
        ''', (vehicle_id,))
        return [dict(row) for row in cursor.fetchall()]
def get_bookings_by_vehicle(vehicle_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, v.vin, v.make, v.model, 
                   sc.name as service_center_name, sc.location
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.id
            JOIN service_centers sc ON b.service_center_id = sc.id
            WHERE b.vehicle_id = ?
            ORDER BY b.booking_date DESC, b.booking_time DESC
        ''', (vehicle_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_bookings_by_service_center(service_center_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, v.vin, v.make, v.model, v.owner_name, v.owner_phone
            FROM bookings b
            JOIN vehicles v ON b.vehicle_id = v.id
            WHERE b.service_center_id = ?
            ORDER BY b.booking_date, b.booking_time
        ''', (service_center_id,))
        return [dict(row) for row in cursor.fetchall()]
def get_garage_by_id(garage_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM garages WHERE id = ?", (garage_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_garage_load(garage_id, load_change):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE garages 
            SET current_load = current_load + ? 
            WHERE id = ? AND current_load + ? <= capacity
        ''', (load_change, garage_id, load_change))
        conn.commit()
        return cursor.rowcount > 0
def get_part_by_id(part_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM parts_catalog WHERE id = ?", (part_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_part_stock(part_id, quantity_change):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE parts_catalog 
            SET stock_quantity = stock_quantity + ? 
            WHERE id = ?
        ''', (quantity_change, part_id))
        conn.commit()
        return cursor.rowcount > 0
def get_service_center_by_id(service_center_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM service_centers WHERE id = ?", (service_center_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_service_center_load(service_center_id, load_change):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE service_centers 
            SET current_load = current_load + ? 
            WHERE id = ? AND current_load + ? <= capacity
        ''', (load_change, service_center_id, load_change))
        conn.commit()
        return cursor.rowcount > 0
def get_breakdown_incident_by_id(incident_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, v.vin, v.make, v.model, g.name as garage_name
            FROM breakdown_incidents b
            JOIN vehicles v ON b.vehicle_id = v.id
            LEFT JOIN garages g ON b.garage_id = g.id
            WHERE b.id = ?
        ''', (incident_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def complete_breakdown_incident(incident_id, parts_used, total_cost, actual_fix_time):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE breakdown_incidents 
            SET status = 'completed', parts_used = ?, total_cost = ?, actual_fix_time = ?
            WHERE id = ?
        ''', (json.dumps(parts_used) if parts_used else None, total_cost, actual_fix_time, incident_id))
        conn.commit()
def get_vehicle_health_trend(vehicle_id, days=30):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT date(timestamp) as date, 
                   AVG(engine_temp) as avg_engine_temp,
                   AVG(oil_pressure) as avg_oil_pressure,
                   AVG(battery_voltage) as avg_battery_voltage
            FROM telemetry_data
            WHERE vehicle_id = ? AND timestamp >= date('now', ?)
            GROUP BY date(timestamp)
            ORDER BY date
        ''', (vehicle_id, f'-{days} days'))
        return [dict(row) for row in cursor.fetchall()]

def get_maintenance_history(vehicle_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, sc.name as service_center_name, f.rating, f.comments
            FROM bookings b
            JOIN service_centers sc ON b.service_center_id = sc.id
            LEFT JOIN feedback f ON b.id = f.booking_id
            WHERE b.vehicle_id = ? AND b.status = 'completed'
            ORDER BY b.completed_at DESC
        ''', (vehicle_id,))
        return [dict(row) for row in cursor.fetchall()]
def search_vehicles(search_term):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM vehicles 
            WHERE vin LIKE ? OR make LIKE ? OR model LIKE ? OR owner_name LIKE ?
            ORDER BY created_at DESC
        ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        return [dict(row) for row in cursor.fetchall()]

def delete_vehicle(vehicle_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        conn.commit()
        return cursor.rowcount > 0
# In database.py - Add these functions:

def update_breakdown_status(incident_id, status, technician_notes=None):
    """Update breakdown status: 'assigned' → 'in_progress' → 'completed'"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE breakdown_incidents 
            SET status = ?, technician_notes = ?
            WHERE id = ?
        ''', (status, technician_notes, incident_id))
        conn.commit()

def start_breakdown_fix(incident_id, technician_id=None):
    """Garage starts working on the fix"""
    update_breakdown_status(incident_id, 'in_progress')
    # Log start time, assign technician, etc.

def complete_breakdown_fix(incident_id, parts_used, total_cost, actual_fix_time, notes):
    """Garage completes the fix"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE breakdown_incidents 
            SET status = 'completed', 
                parts_used = ?, 
                total_cost = ?, 
                actual_fix_time = ?,
                technician_notes = ?
            WHERE id = ?
        ''', (json.dumps(parts_used), total_cost, actual_fix_time, notes, incident_id))
        conn.commit()
def use_parts_for_breakdown(incident_id, parts_list):
    """Record parts used and update inventory"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for part in parts_list:
            # Update inventory
            cursor.execute('''
                UPDATE parts_catalog 
                SET stock_quantity = stock_quantity - ?
                WHERE part_number = ? AND stock_quantity >= ?
            ''', (part['quantity'], part['part_number'], part['quantity']))
            
            # Record usage
            cursor.execute('''
                INSERT INTO parts_usage (incident_id, part_number, quantity, unit_price)
                VALUES (?, ?, ?, ?)
            ''', (incident_id, part['part_number'], part['quantity'], part['price']))
        conn.commit()
def generate_breakdown_invoice(incident_id):
    """Create final invoice for breakdown fix"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, v.*, g.name as garage_name, g.phone as garage_phone,
                   p.parts_used, p.labor_cost, p.total_cost
            FROM breakdown_incidents b
            JOIN vehicles v ON b.vehicle_id = v.id
            JOIN garages g ON b.garage_id = g.id
            LEFT JOIN breakdown_payments p ON b.id = p.incident_id
            WHERE b.id = ?
        ''', (incident_id,))
        return dict(cursor.fetchone())
# Add to database.py

def get_all_garages():
    """Get all garages"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM garages ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

def get_active_breakdowns_for_garage(garage_id):
    """Get active breakdowns for a specific garage"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, v.make, v.model, v.year, v.owner_name, v.owner_phone, v.vin
            FROM breakdown_incidents b
            JOIN vehicles v ON b.vehicle_id = v.id
            WHERE b.garage_id = ? AND b.status IN ('assigned', 'in_progress', 'on_hold')
            ORDER BY b.reported_at ASC
        ''', (garage_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_breakdowns_by_garage_and_status(garage_id, status_list):
    """Get breakdowns by garage and status"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(status_list))
        query = f'''
            SELECT b.*, v.make, v.model, v.year, v.owner_name, v.owner_phone, v.vin
            FROM breakdown_incidents b
            JOIN vehicles v ON b.vehicle_id = v.id
            WHERE b.garage_id = ? AND b.status IN ({placeholders})
            ORDER BY b.reported_at ASC
        '''
        cursor.execute(query, [garage_id] + status_list)
        return [dict(row) for row in cursor.fetchall()]

def get_completed_breakdowns_today(garage_id):
    """Get number of breakdowns completed today"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM breakdown_incidents 
            WHERE garage_id = ? AND status = 'completed' 
            AND DATE(completed_at) = DATE('now')
        ''', (garage_id,))
        return cursor.fetchone()[0]

# Add tables for technicians and parts_usage
def init_database():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # ... existing table creation code ...
        
        # Add technicians table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS technicians (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garage_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                specialization TEXT,
                contact TEXT NOT NULL,
                experience_years INTEGER DEFAULT 0,
                status TEXT DEFAULT 'available',
                current_incident_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (garage_id) REFERENCES garages(id),
                FOREIGN KEY (current_incident_id) REFERENCES breakdown_incidents(id)
            )
        ''')
        
        # Add parts_usage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parts_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id INTEGER NOT NULL,
                part_number TEXT NOT NULL,
                part_name TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                unit_price REAL NOT NULL,
                total_price REAL GENERATED ALWAYS AS (quantity * unit_price) VIRTUAL,
                used_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (incident_id) REFERENCES breakdown_incidents(id)
            )
        ''')
        
        conn.commit()

def create_technician(garage_id, name, specialization, contact, experience_years):
    """Add a new technician"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO technicians (garage_id, name, specialization, contact, experience_years)
            VALUES (?, ?, ?, ?, ?)
        ''', (garage_id, name, specialization, contact, experience_years))
        conn.commit()
        return cursor.lastrowid

def get_technician_by_id(technician_id):
    """Get technician by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM technicians WHERE id = ?", (technician_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_garage_analytics(garage_id):
    """Get analytics for a garage"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get monthly completions
        cursor.execute('''
            SELECT strftime('%Y-%m', completed_at) as month, 
                   COUNT(*) as count,
                   SUM(total_cost) as revenue
            FROM breakdown_incidents
            WHERE garage_id = ? AND status = 'completed' AND completed_at IS NOT NULL
            GROUP BY strftime('%Y-%m', completed_at)
            ORDER BY month DESC
            LIMIT 6
        ''', (garage_id,))
        
        monthly_data = cursor.fetchall()
        monthly_completions = {row['month']: row['count'] for row in monthly_data}
        monthly_revenue = {row['month']: row['revenue'] or 0 for row in monthly_data}
        
        # Get average response time
        cursor.execute('''
            SELECT AVG(
                (julianday(updated_at) - julianday(reported_at)) * 24 * 60
            ) as avg_response_time
            FROM breakdown_incidents
            WHERE garage_id = ? AND status = 'completed'
        ''', (garage_id,))
        
        avg_response_time = cursor.fetchone()[0] or 0
        
        return {
            'monthly_completions': monthly_completions,
            'monthly_revenue': monthly_revenue,
            'avg_response_time': avg_response_time,
            'response_rate': 95  # Placeholder
        }

def get_garage_feedback(garage_id):
    """Get feedback for garage's completed jobs"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT f.*, v.make, v.model
            FROM feedback f
            JOIN bookings b ON f.booking_id = b.id
            JOIN vehicles v ON f.vehicle_id = v.id
            JOIN breakdown_incidents bi ON b.vehicle_id = v.id
            WHERE bi.garage_id = ?
            ORDER BY f.created_at DESC
            LIMIT 10
        ''', (garage_id,))
        return [dict(row) for row in cursor.fetchall()]

# Add this to database.py (if not already there)

def get_all_garages():
    """Get all garages"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM garages ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

def get_breakdowns_for_garage(garage_id):
    """Get all breakdowns for a specific garage"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, v.make, v.model, v.year, v.owner_name, v.owner_phone, v.vin
            FROM breakdown_incidents b
            JOIN vehicles v ON b.vehicle_id = v.id
            WHERE b.garage_id = ? 
            ORDER BY 
                CASE b.status 
                    WHEN 'in_progress' THEN 1
                    WHEN 'assigned' THEN 2
                    WHEN 'reported' THEN 3
                    WHEN 'completed' THEN 4
                    ELSE 5
                END,
                b.reported_at ASC
        ''', (garage_id,))
        return [dict(row) for row in cursor.fetchall()]

def update_breakdown_status(incident_id, status, technician_notes=None):
    """Update breakdown status"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE breakdown_incidents 
            SET status = ?, technician_notes = ?
            WHERE id = ?
        ''', (status, technician_notes, incident_id))
        conn.commit()
        return cursor.rowcount > 0
def update_breakdown_status(incident_id, status, technician_notes=None):
    """Update breakdown status"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if technician_notes:
            cursor.execute('''
                UPDATE breakdown_incidents 
                SET status = ?, technician_notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, technician_notes, incident_id))
        else:
            cursor.execute('''
                UPDATE breakdown_incidents 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, incident_id))
        conn.commit()
        return cursor.rowcount > 0
def complete_breakdown_incident(incident_id, parts_used, total_cost, actual_fix_time, technician_notes=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE breakdown_incidents 
            SET status = 'completed', 
                parts_used = ?, 
                total_cost = ?, 
                actual_fix_time = ?,
                technician_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (json.dumps(parts_used) if parts_used else None, 
              total_cost, actual_fix_time, technician_notes, incident_id))
        conn.commit()
def update_database_schema():
    """Add missing columns to existing tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            # Add technician_notes column to breakdown_incidents if it doesn't exist
            cursor.execute("PRAGMA table_info(breakdown_incidents)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'technician_notes' not in columns:
                cursor.execute('''
                    ALTER TABLE breakdown_incidents 
                    ADD COLUMN technician_notes TEXT
                ''')
                print("Added technician_notes column to breakdown_incidents")
            
            if 'updated_at' not in columns:
                cursor.execute('''
                    ALTER TABLE breakdown_incidents 
                    ADD COLUMN updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                ''')
                print("Added updated_at column to breakdown_incidents")
            
            conn.commit()
            print("Database schema updated successfully!")
            
        except Exception as e:
            print(f"Error updating schema: {e}")
            conn.rollback()
