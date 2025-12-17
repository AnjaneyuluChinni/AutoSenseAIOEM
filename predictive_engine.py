import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

class PredictiveMaintenanceEngine:
    
    COMPONENT_FAILURE_PATTERNS = {
        'engine': {
            'indicators': ['engine_temp', 'oil_pressure', 'vibration_level', 'rpm'],
            'failure_threshold': 0.7,
            'mtbf_days': 365
        },
        'battery': {
            'indicators': ['battery_voltage'],
            'failure_threshold': 0.6,
            'mtbf_days': 730
        },
        'brakes': {
            'indicators': ['brake_wear', 'vibration_level'],
            'failure_threshold': 0.65,
            'mtbf_days': 180
        },
        'cooling_system': {
            'indicators': ['engine_temp', 'coolant_temp'],
            'failure_threshold': 0.7,
            'mtbf_days': 545
        },
        'tires': {
            'indicators': ['tire_pressure_fl', 'tire_pressure_fr', 'tire_pressure_rl', 'tire_pressure_rr'],
            'failure_threshold': 0.5,
            'mtbf_days': 365
        },
        'transmission': {
            'indicators': ['vibration_level', 'rpm', 'speed'],
            'failure_threshold': 0.75,
            'mtbf_days': 730
        }
    }
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.failure_predictor = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False
        self._generate_synthetic_training_data()
    
    def _generate_synthetic_training_data(self):
        np.random.seed(42)
        n_samples = 1000
        
        normal_data = {
            'engine_temp': np.random.normal(95, 5, n_samples),
            'oil_pressure': np.random.normal(45, 10, n_samples),
            'battery_voltage': np.random.normal(13.5, 0.5, n_samples),
            'rpm': np.random.normal(3000, 1000, n_samples),
            'speed': np.random.normal(60, 20, n_samples),
            'vibration_level': np.random.normal(1.0, 0.3, n_samples),
            'brake_wear': np.random.normal(20, 10, n_samples),
            'coolant_temp': np.random.normal(90, 5, n_samples),
            'tire_pressure_avg': np.random.normal(32, 1, n_samples)
        }
        
        n_anomalies = 200
        anomaly_data = {
            'engine_temp': np.random.normal(115, 10, n_anomalies),
            'oil_pressure': np.random.normal(20, 5, n_anomalies),
            'battery_voltage': np.random.normal(11.0, 0.8, n_anomalies),
            'rpm': np.random.normal(5500, 800, n_anomalies),
            'speed': np.random.normal(40, 30, n_anomalies),
            'vibration_level': np.random.normal(3.5, 1.0, n_anomalies),
            'brake_wear': np.random.normal(65, 15, n_anomalies),
            'coolant_temp': np.random.normal(115, 8, n_anomalies),
            'tire_pressure_avg': np.random.normal(28, 3, n_anomalies)
        }
        
        normal_df = pd.DataFrame(normal_data)
        normal_df['label'] = 0
        
        anomaly_df = pd.DataFrame(anomaly_data)
        anomaly_df['label'] = 1
        
        self.training_data = pd.concat([normal_df, anomaly_df], ignore_index=True)
        
        X = self.training_data.drop('label', axis=1)
        y = self.training_data['label']
        
        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        
        self.anomaly_detector.fit(X_scaled)
        self.failure_predictor.fit(X_scaled, y)
        self.is_trained = True
    
    def prepare_features(self, telemetry: Dict) -> np.ndarray:
        tire_pressures = [
            telemetry.get('tire_pressure_fl', 32),
            telemetry.get('tire_pressure_fr', 32),
            telemetry.get('tire_pressure_rl', 32),
            telemetry.get('tire_pressure_rr', 32)
        ]
        
        features = np.array([
            telemetry.get('engine_temp', 95),
            telemetry.get('oil_pressure', 45),
            telemetry.get('battery_voltage', 13.5),
            telemetry.get('rpm', 3000),
            telemetry.get('speed', 60),
            telemetry.get('vibration_level', 1.0),
            telemetry.get('brake_wear', 20),
            telemetry.get('coolant_temp', 90),
            np.mean(tire_pressures)
        ]).reshape(1, -1)
        
        return features
    
    def detect_anomalies(self, telemetry: Dict) -> Dict:
        features = self.prepare_features(telemetry)
        features_scaled = self.scaler.transform(features)
        
        anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]
        is_anomaly = self.anomaly_detector.predict(features_scaled)[0] == -1
        
        anomaly_probability = 1 / (1 + np.exp(anomaly_score * 2))
        
        return {
            'is_anomaly': is_anomaly,
            'anomaly_score': float(anomaly_score),
            'anomaly_probability': float(anomaly_probability),
            'confidence': float(abs(anomaly_score) / 0.5) if abs(anomaly_score) < 0.5 else 1.0
        }
    
    def predict_failure(self, telemetry: Dict) -> Dict:
        features = self.prepare_features(telemetry)
        features_scaled = self.scaler.transform(features)
        
        failure_proba = self.failure_predictor.predict_proba(features_scaled)[0]
        failure_probability = failure_proba[1] if len(failure_proba) > 1 else 0.0
        
        risk_level = 'low'
        if failure_probability >= 0.7:
            risk_level = 'critical'
        elif failure_probability >= 0.4:
            risk_level = 'high'
        elif failure_probability >= 0.2:
            risk_level = 'medium'
        
        return {
            'failure_probability': float(failure_probability),
            'risk_level': risk_level,
            'confidence': float(max(failure_proba))
        }
    
    def analyze_component_health(self, telemetry: Dict) -> Dict[str, Dict]:
        component_health = {}
        
        for component, config in self.COMPONENT_FAILURE_PATTERNS.items():
            indicators = config['indicators']
            threshold = config['failure_threshold']
            mtbf = config['mtbf_days']
            
            health_scores = []
            issues = []
            
            for indicator in indicators:
                value = telemetry.get(indicator)
                if value is None:
                    continue
                
                indicator_health = self._calculate_indicator_health(indicator, value)
                health_scores.append(indicator_health['score'])
                
                if indicator_health['status'] != 'normal':
                    issues.append({
                        'indicator': indicator,
                        'value': value,
                        'status': indicator_health['status'],
                        'deviation': indicator_health['deviation']
                    })
            
            if health_scores:
                avg_health = np.mean(health_scores)
                failure_risk = 1 - (avg_health / 100)
                
                if failure_risk >= threshold:
                    days_to_failure = int(mtbf * (1 - failure_risk) * 0.3)
                else:
                    days_to_failure = int(mtbf * (1 - failure_risk))
                
                predicted_failure_date = datetime.now() + timedelta(days=max(1, days_to_failure))
                
                status = 'healthy'
                if avg_health < 50:
                    status = 'critical'
                elif avg_health < 70:
                    status = 'warning'
                
                component_health[component] = {
                    'health_score': round(avg_health, 1),
                    'failure_risk': round(failure_risk, 3),
                    'status': status,
                    'days_to_potential_failure': days_to_failure,
                    'predicted_failure_date': predicted_failure_date.strftime('%Y-%m-%d'),
                    'issues': issues,
                    'maintenance_urgency': 'immediate' if days_to_failure < 7 else 'soon' if days_to_failure < 30 else 'scheduled'
                }
        
        return component_health
    
    def _calculate_indicator_health(self, indicator: str, value: float) -> Dict:
        normal_ranges = {
            'engine_temp': (85, 105),
            'oil_pressure': (25, 65),
            'battery_voltage': (12.4, 14.7),
            'rpm': (800, 6500),
            'speed': (0, 120),
            'vibration_level': (0.1, 2.0),
            'brake_wear': (0, 30),
            'coolant_temp': (80, 100),
            'tire_pressure_fl': (30, 35),
            'tire_pressure_fr': (30, 35),
            'tire_pressure_rl': (30, 35),
            'tire_pressure_rr': (30, 35)
        }
        
        if indicator not in normal_ranges:
            return {'score': 85, 'status': 'unknown', 'deviation': 0}
        
        min_val, max_val = normal_ranges[indicator]
        mid_val = (min_val + max_val) / 2
        range_size = max_val - min_val
        
        deviation = abs(value - mid_val) / (range_size / 2)
        
        if value < min_val:
            deviation = (min_val - value) / (range_size * 0.5) + 1
        elif value > max_val:
            deviation = (value - max_val) / (range_size * 0.5) + 1
        
        score = max(0, 100 - (deviation * 30))
        
        status = 'normal'
        if score < 50:
            status = 'critical'
        elif score < 70:
            status = 'warning'
        
        return {
            'score': round(score, 1),
            'status': status,
            'deviation': round(deviation, 2)
        }
    
    def generate_prediction_report(self, telemetry: Dict, vehicle_info: Dict = None) -> Dict:
        anomaly_result = self.detect_anomalies(telemetry)
        failure_result = self.predict_failure(telemetry)
        component_health = self.analyze_component_health(telemetry)
        
        critical_components = [c for c, h in component_health.items() if h['status'] == 'critical']
        warning_components = [c for c, h in component_health.items() if h['status'] == 'warning']
        
        overall_health = np.mean([h['health_score'] for h in component_health.values()]) if component_health else 100
        
        recommendations = []
        
        for component, health in component_health.items():
            if health['status'] == 'critical':
                recommendations.append({
                    'priority': 'high',
                    'component': component,
                    'action': f'Immediate inspection required for {component}',
                    'reason': f'Health score: {health["health_score"]}%, Risk: {health["failure_risk"]*100:.1f}%',
                    'deadline': health['predicted_failure_date']
                })
            elif health['status'] == 'warning':
                recommendations.append({
                    'priority': 'medium',
                    'component': component,
                    'action': f'Schedule maintenance for {component}',
                    'reason': f'Health score: {health["health_score"]}%, Risk: {health["failure_risk"]*100:.1f}%',
                    'deadline': health['predicted_failure_date']
                })
        
        recommendations.sort(key=lambda x: 0 if x['priority'] == 'high' else 1)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'vehicle_info': vehicle_info,
            'anomaly_detection': anomaly_result,
            'failure_prediction': failure_result,
            'component_health': component_health,
            'overall_health_score': round(overall_health, 1),
            'critical_components': critical_components,
            'warning_components': warning_components,
            'recommendations': recommendations,
            'requires_immediate_attention': len(critical_components) > 0 or failure_result['risk_level'] == 'critical'
        }

def get_prediction_engine() -> PredictiveMaintenanceEngine:
    return PredictiveMaintenanceEngine()
