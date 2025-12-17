import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TelemetrySimulator:
    
    NORMAL_RANGES = {
        'engine_temp': (85, 105),
        'oil_pressure': (25, 65),
        'battery_voltage': (12.4, 14.7),
        'rpm': (800, 6500),
        'speed': (0, 120),
        'vibration_level': (0.1, 2.0),
        'brake_wear': (0, 30),
        'tire_pressure': (30, 35),
        'fuel_level': (10, 100),
        'coolant_temp': (80, 100)
    }
    
    WARNING_THRESHOLDS = {
        'engine_temp': {'min': 70, 'max': 110},
        'oil_pressure': {'min': 20, 'max': 70},
        'battery_voltage': {'min': 11.8, 'max': 15.0},
        'vibration_level': {'min': 0, 'max': 3.5},
        'brake_wear': {'min': 0, 'max': 60},
        'tire_pressure': {'min': 28, 'max': 38},
        'coolant_temp': {'min': 70, 'max': 115}
    }
    
    CRITICAL_THRESHOLDS = {
        'engine_temp': {'min': 60, 'max': 125},
        'oil_pressure': {'min': 15, 'max': 80},
        'battery_voltage': {'min': 10.5, 'max': 16.0},
        'vibration_level': {'min': 0, 'max': 5.0},
        'brake_wear': {'min': 0, 'max': 80},
        'tire_pressure': {'min': 25, 'max': 42},
        'coolant_temp': {'min': 60, 'max': 130}
    }
    
    ERROR_CODES = {
        'P0300': 'Random/Multiple Cylinder Misfire Detected',
        'P0171': 'System Too Lean (Bank 1)',
        'P0420': 'Catalyst System Efficiency Below Threshold',
        'P0128': 'Coolant Thermostat Temperature Below Regulating',
        'P0455': 'Evaporative Emission Control System Leak Detected',
        'P0507': 'Idle Air Control System RPM Higher Than Expected',
        'P0700': 'Transmission Control System Malfunction',
        'P0340': 'Camshaft Position Sensor Circuit Malfunction',
        'C0035': 'Left Front Wheel Speed Sensor Circuit',
        'C0040': 'Right Front Wheel Speed Sensor Circuit',
        'B1000': 'ECU Malfunction',
        'U0100': 'Lost Communication With ECM/PCM'
    }
    
    def __init__(self, vehicle_id: int, scenario: str = 'normal'):
        self.vehicle_id = vehicle_id
        self.scenario = scenario
        self.degradation_factor = 0.0
        self.error_probability = 0.01
        
        if scenario == 'degrading':
            self.degradation_factor = random.uniform(0.1, 0.3)
            self.error_probability = 0.05
        elif scenario == 'critical':
            self.degradation_factor = random.uniform(0.4, 0.7)
            self.error_probability = 0.15
        elif scenario == 'random':
            self.degradation_factor = random.uniform(0, 0.5)
            self.error_probability = random.uniform(0.01, 0.1)
    
    def generate_telemetry(self) -> Dict:
        engine_temp = self._generate_with_degradation('engine_temp', bias_high=True)
        oil_pressure = self._generate_with_degradation('oil_pressure', bias_high=False)
        battery_voltage = self._generate_with_degradation('battery_voltage', bias_high=False)
        rpm = random.randint(*self.NORMAL_RANGES['rpm'])
        speed = random.randint(0, 80) if rpm < 2000 else random.randint(40, 120)
        vibration_level = self._generate_with_degradation('vibration_level', bias_high=True)
        brake_wear = self._generate_with_degradation('brake_wear', bias_high=True)
        
        tire_pressures = self._generate_tire_pressures()
        
        fuel_level = random.uniform(*self.NORMAL_RANGES['fuel_level'])
        coolant_temp = self._generate_with_degradation('coolant_temp', bias_high=True)
        
        error_codes = self._generate_error_codes()
        
        return {
            'vehicle_id': self.vehicle_id,
            'timestamp': datetime.now().isoformat(),
            'engine_temp': round(engine_temp, 1),
            'oil_pressure': round(oil_pressure, 1),
            'battery_voltage': round(battery_voltage, 2),
            'rpm': rpm,
            'speed': speed,
            'vibration_level': round(vibration_level, 2),
            'brake_wear': round(brake_wear, 1),
            'tire_pressure_fl': round(tire_pressures['fl'], 1),
            'tire_pressure_fr': round(tire_pressures['fr'], 1),
            'tire_pressure_rl': round(tire_pressures['rl'], 1),
            'tire_pressure_rr': round(tire_pressures['rr'], 1),
            'fuel_level': round(fuel_level, 1),
            'coolant_temp': round(coolant_temp, 1),
            'error_codes': error_codes
        }
    
    def _generate_with_degradation(self, param: str, bias_high: bool = True) -> float:
        min_val, max_val = self.NORMAL_RANGES[param]
        base_value = random.uniform(min_val, max_val)
        
        if self.degradation_factor > 0:
            if bias_high:
                degradation_shift = (max_val - min_val) * self.degradation_factor * random.uniform(0.5, 1.5)
                base_value += degradation_shift
            else:
                degradation_shift = (max_val - min_val) * self.degradation_factor * random.uniform(0.5, 1.5)
                base_value -= degradation_shift
        
        noise = random.gauss(0, (max_val - min_val) * 0.05)
        return base_value + noise
    
    def _generate_tire_pressures(self) -> Dict[str, float]:
        base_pressure = random.uniform(*self.NORMAL_RANGES['tire_pressure'])
        
        if random.random() < self.degradation_factor:
            low_tire = random.choice(['fl', 'fr', 'rl', 'rr'])
            pressures = {
                'fl': base_pressure + random.gauss(0, 1),
                'fr': base_pressure + random.gauss(0, 1),
                'rl': base_pressure + random.gauss(0, 1),
                'rr': base_pressure + random.gauss(0, 1)
            }
            pressures[low_tire] -= random.uniform(3, 8)
        else:
            pressures = {
                'fl': base_pressure + random.gauss(0, 0.5),
                'fr': base_pressure + random.gauss(0, 0.5),
                'rl': base_pressure + random.gauss(0, 0.5),
                'rr': base_pressure + random.gauss(0, 0.5)
            }
        
        return pressures
    
    def _generate_error_codes(self) -> List[str]:
        error_codes = []
        
        if random.random() < self.error_probability:
            num_errors = random.randint(1, min(3, int(self.degradation_factor * 5) + 1))
            error_codes = random.sample(list(self.ERROR_CODES.keys()), num_errors)
        
        return error_codes
    
    def generate_historical_data(self, days: int = 30, readings_per_day: int = 4) -> List[Dict]:
        historical_data = []
        current_time = datetime.now()
        
        initial_degradation = max(0, self.degradation_factor - 0.3)
        degradation_increment = (self.degradation_factor - initial_degradation) / (days * readings_per_day)
        
        for day in range(days, 0, -1):
            for reading in range(readings_per_day):
                timestamp = current_time - timedelta(days=day, hours=reading * 6)
                
                temp_degradation = initial_degradation + (degradation_increment * ((days - day) * readings_per_day + reading))
                original_degradation = self.degradation_factor
                self.degradation_factor = temp_degradation
                
                telemetry = self.generate_telemetry()
                telemetry['timestamp'] = timestamp.isoformat()
                historical_data.append(telemetry)
                
                self.degradation_factor = original_degradation
        
        return historical_data

def generate_fleet_telemetry(vehicle_ids: List[int], scenario_distribution: Dict[str, float] = None) -> List[Dict]:
    if scenario_distribution is None:
        scenario_distribution = {
            'normal': 0.6,
            'degrading': 0.25,
            'critical': 0.1,
            'random': 0.05
        }
    
    fleet_telemetry = []
    
    for vehicle_id in vehicle_ids:
        scenario = np.random.choice(
            list(scenario_distribution.keys()),
            p=list(scenario_distribution.values())
        )
        
        simulator = TelemetrySimulator(vehicle_id, scenario)
        telemetry = simulator.generate_telemetry()
        telemetry['scenario'] = scenario
        fleet_telemetry.append(telemetry)
    
    return fleet_telemetry

def analyze_telemetry_anomalies(telemetry: Dict) -> Dict:
    anomalies = []
    severity_score = 0
    
    checks = [
        ('engine_temp', telemetry.get('engine_temp', 90), 'Engine Temperature'),
        ('oil_pressure', telemetry.get('oil_pressure', 40), 'Oil Pressure'),
        ('battery_voltage', telemetry.get('battery_voltage', 12.6), 'Battery Voltage'),
        ('vibration_level', telemetry.get('vibration_level', 1.0), 'Vibration Level'),
        ('brake_wear', telemetry.get('brake_wear', 20), 'Brake Wear'),
        ('coolant_temp', telemetry.get('coolant_temp', 90), 'Coolant Temperature')
    ]
    
    for param, value, display_name in checks:
        warning = TelemetrySimulator.WARNING_THRESHOLDS.get(param, {})
        critical = TelemetrySimulator.CRITICAL_THRESHOLDS.get(param, {})
        
        if value < critical.get('min', float('-inf')) or value > critical.get('max', float('inf')):
            anomalies.append({
                'parameter': display_name,
                'value': value,
                'severity': 'critical',
                'message': f'{display_name} is at critical level: {value}'
            })
            severity_score += 30
        elif value < warning.get('min', float('-inf')) or value > warning.get('max', float('inf')):
            anomalies.append({
                'parameter': display_name,
                'value': value,
                'severity': 'warning',
                'message': f'{display_name} is outside normal range: {value}'
            })
            severity_score += 15
    
    tire_pressures = [
        telemetry.get('tire_pressure_fl', 32),
        telemetry.get('tire_pressure_fr', 32),
        telemetry.get('tire_pressure_rl', 32),
        telemetry.get('tire_pressure_rr', 32)
    ]
    
    for i, (position, pressure) in enumerate(zip(['Front Left', 'Front Right', 'Rear Left', 'Rear Right'], tire_pressures)):
        if pressure < 28 or pressure > 38:
            severity = 'critical' if pressure < 25 or pressure > 42 else 'warning'
            anomalies.append({
                'parameter': f'Tire Pressure ({position})',
                'value': pressure,
                'severity': severity,
                'message': f'{position} tire pressure abnormal: {pressure} PSI'
            })
            severity_score += 20 if severity == 'critical' else 10
    
    error_codes = telemetry.get('error_codes', [])
    if error_codes:
        for code in error_codes:
            description = TelemetrySimulator.ERROR_CODES.get(code, 'Unknown Error')
            anomalies.append({
                'parameter': 'Error Code',
                'value': code,
                'severity': 'critical' if code.startswith('P07') or code.startswith('U') else 'warning',
                'message': f'{code}: {description}'
            })
            severity_score += 25
    
    overall_status = 'healthy'
    if severity_score >= 50:
        overall_status = 'critical'
    elif severity_score >= 20:
        overall_status = 'warning'
    
    health_score = max(0, 100 - severity_score)
    
    return {
        'anomalies': anomalies,
        'severity_score': severity_score,
        'overall_status': overall_status,
        'health_score': health_score,
        'anomaly_count': len(anomalies)
    }
