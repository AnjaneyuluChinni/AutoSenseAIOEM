import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import random

from database import log_agent_action, create_alert, create_booking, get_all_service_centers, update_vehicle_health, create_rca_report
from telemetry import analyze_telemetry_anomalies
from predictive_engine import get_prediction_engine

class AgentType(Enum):
    MASTER = "master_agent"
    PREDICTION = "prediction_agent"
    DIAGNOSIS = "diagnosis_agent"
    SCHEDULING = "scheduling_agent"
    CUSTOMER = "customer_agent"
    RCA_FEEDBACK = "rca_feedback_agent"

@dataclass
class AgentMessage:
    sender: str
    recipient: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    priority: str = "normal"

class BaseAgent:
    
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.name = agent_type.value
        self.message_queue: List[AgentMessage] = []
        self.execution_log: List[Dict] = []
    
    def receive_message(self, message: AgentMessage):
        self.message_queue.append(message)
    
    def log_execution(self, action: str, input_data: Dict, output_data: Dict, reasoning: str, execution_time: float, status: str = 'success'):
        log_entry = {
            'agent': self.name,
            'action': action,
            'input': input_data,
            'output': output_data,
            'reasoning': reasoning,
            'execution_time': execution_time,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        self.execution_log.append(log_entry)
        log_agent_action(self.name, action, input_data, output_data, reasoning, execution_time, status)
        return log_entry
    
    def process(self, data: Dict) -> Dict:
        raise NotImplementedError("Subclasses must implement process method")

class PredictionAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(AgentType.PREDICTION)
        self.prediction_engine = get_prediction_engine()
    
    def process(self, data: Dict) -> Dict:
        start_time = time.time()
        
        telemetry = data.get('telemetry', {})
        vehicle_info = data.get('vehicle_info', {})
        
        report = self.prediction_engine.generate_prediction_report(telemetry, vehicle_info)
        
        alerts_generated = []
        for rec in report.get('recommendations', []):
            if rec['priority'] == 'high':
                alerts_generated.append({
                    'component': rec['component'],
                    'severity': 'critical',
                    'action': rec['action']
                })
        
        reasoning = f"Analyzed telemetry data. Overall health: {report['overall_health_score']}%. "
        reasoning += f"Found {len(report['critical_components'])} critical and {len(report['warning_components'])} warning components. "
        if report['requires_immediate_attention']:
            reasoning += "Immediate attention required."
        
        execution_time = time.time() - start_time
        
        result = {
            'prediction_report': report,
            'alerts_to_create': alerts_generated,
            'requires_diagnosis': len(report['critical_components']) > 0,
            'requires_scheduling': report['requires_immediate_attention']
        }
        
        self.log_execution(
            action='predict_maintenance',
            input_data={'vehicle_id': vehicle_info.get('id'), 'telemetry_snapshot': True},
            output_data={'health_score': report['overall_health_score'], 'critical_count': len(report['critical_components'])},
            reasoning=reasoning,
            execution_time=execution_time
        )
        
        return result

class DiagnosisAgent(BaseAgent):
    
    DIAGNOSIS_KNOWLEDGE_BASE = {
        'engine': {
            'high_temp': {
                'possible_causes': ['Coolant leak', 'Thermostat failure', 'Radiator blockage', 'Water pump failure'],
                'recommended_actions': ['Check coolant level', 'Inspect thermostat', 'Flush radiator', 'Test water pump'],
                'severity_multiplier': 1.5
            },
            'low_oil_pressure': {
                'possible_causes': ['Oil leak', 'Worn oil pump', 'Clogged oil filter', 'Wrong oil viscosity'],
                'recommended_actions': ['Check oil level', 'Replace oil filter', 'Inspect for leaks', 'Oil change'],
                'severity_multiplier': 1.8
            },
            'high_vibration': {
                'possible_causes': ['Engine mount wear', 'Misfiring cylinder', 'Unbalanced components', 'Worn bearings'],
                'recommended_actions': ['Check engine mounts', 'Inspect spark plugs', 'Balance rotating parts', 'Check bearings'],
                'severity_multiplier': 1.3
            }
        },
        'battery': {
            'low_voltage': {
                'possible_causes': ['Aging battery', 'Alternator failure', 'Parasitic drain', 'Loose connections'],
                'recommended_actions': ['Test battery capacity', 'Check alternator output', 'Inspect electrical system', 'Clean terminals'],
                'severity_multiplier': 1.2
            }
        },
        'brakes': {
            'high_wear': {
                'possible_causes': ['Normal wear', 'Aggressive driving', 'Stuck caliper', 'Warped rotors'],
                'recommended_actions': ['Replace brake pads', 'Inspect calipers', 'Check rotors', 'Brake fluid flush'],
                'severity_multiplier': 1.6
            }
        },
        'cooling_system': {
            'high_coolant_temp': {
                'possible_causes': ['Low coolant', 'Thermostat stuck', 'Fan failure', 'Head gasket leak'],
                'recommended_actions': ['Top up coolant', 'Replace thermostat', 'Test cooling fan', 'Pressure test system'],
                'severity_multiplier': 1.7
            }
        },
        'tires': {
            'low_pressure': {
                'possible_causes': ['Slow puncture', 'Valve stem leak', 'Temperature change', 'Rim damage'],
                'recommended_actions': ['Inspect tire', 'Check valve stem', 'Inflate to spec', 'Check rim seal'],
                'severity_multiplier': 1.1
            }
        }
    }
    
    def __init__(self):
        super().__init__(AgentType.DIAGNOSIS)
    
    def process(self, data: Dict) -> Dict:
        start_time = time.time()
        
        prediction_report = data.get('prediction_report', {})
        component_health = prediction_report.get('component_health', {})
        
        diagnoses = []
        
        for component, health in component_health.items():
            if health['status'] in ['critical', 'warning']:
                diagnosis = self._diagnose_component(component, health)
                diagnoses.append(diagnosis)
        
        prioritized_diagnoses = sorted(diagnoses, key=lambda x: x['priority_score'], reverse=True)
        
        reasoning = f"Diagnosed {len(diagnoses)} components with issues. "
        if prioritized_diagnoses:
            top_issue = prioritized_diagnoses[0]
            reasoning += f"Top priority: {top_issue['component']} - {top_issue['primary_cause']}."
        
        execution_time = time.time() - start_time
        
        result = {
            'diagnoses': prioritized_diagnoses,
            'total_issues': len(diagnoses),
            'requires_immediate_action': any(d['priority_score'] > 80 for d in diagnoses),
            'estimated_repair_time': sum(d.get('estimated_repair_minutes', 30) for d in diagnoses)
        }
        
        self.log_execution(
            action='diagnose_issues',
            input_data={'components_analyzed': list(component_health.keys())},
            output_data={'diagnoses_count': len(diagnoses), 'immediate_action': result['requires_immediate_action']},
            reasoning=reasoning,
            execution_time=execution_time
        )
        
        return result
    
    def _diagnose_component(self, component: str, health: Dict) -> Dict:
        issues = health.get('issues', [])
        
        knowledge = self.DIAGNOSIS_KNOWLEDGE_BASE.get(component, {})
        
        possible_causes = []
        recommended_actions = []
        severity_multiplier = 1.0
        
        for issue in issues:
            indicator = issue.get('indicator', '')
            
            if 'temp' in indicator.lower() and 'high' in issue.get('status', ''):
                kb_entry = knowledge.get('high_temp', knowledge.get('high_coolant_temp', {}))
            elif 'pressure' in indicator.lower() and issue.get('value', 0) < 30:
                kb_entry = knowledge.get('low_oil_pressure', knowledge.get('low_pressure', {}))
            elif 'voltage' in indicator.lower():
                kb_entry = knowledge.get('low_voltage', {})
            elif 'vibration' in indicator.lower():
                kb_entry = knowledge.get('high_vibration', {})
            elif 'wear' in indicator.lower():
                kb_entry = knowledge.get('high_wear', {})
            else:
                kb_entry = {}
            
            possible_causes.extend(kb_entry.get('possible_causes', ['Unknown cause']))
            recommended_actions.extend(kb_entry.get('recommended_actions', ['General inspection']))
            severity_multiplier = max(severity_multiplier, kb_entry.get('severity_multiplier', 1.0))
        
        possible_causes = list(set(possible_causes))[:4]
        recommended_actions = list(set(recommended_actions))[:4]
        
        priority_score = (100 - health['health_score']) * severity_multiplier
        priority_score = min(100, priority_score)
        
        repair_time_map = {
            'engine': 120,
            'battery': 30,
            'brakes': 90,
            'cooling_system': 60,
            'tires': 45,
            'transmission': 180
        }
        
        return {
            'component': component,
            'health_score': health['health_score'],
            'failure_risk': health['failure_risk'],
            'primary_cause': possible_causes[0] if possible_causes else 'Requires inspection',
            'possible_causes': possible_causes,
            'recommended_actions': recommended_actions,
            'priority_score': round(priority_score, 1),
            'estimated_repair_minutes': repair_time_map.get(component, 60),
            'parts_likely_needed': self._estimate_parts(component, possible_causes)
        }
    
    def _estimate_parts(self, component: str, causes: List[str]) -> List[str]:
        parts_map = {
            'engine': ['Oil filter', 'Spark plugs', 'Engine oil'],
            'battery': ['Battery', 'Alternator belt'],
            'brakes': ['Brake pads', 'Brake rotors', 'Brake fluid'],
            'cooling_system': ['Coolant', 'Thermostat', 'Radiator hose'],
            'tires': ['Tire', 'Valve stem', 'TPMS sensor'],
            'transmission': ['Transmission fluid', 'Filter', 'Gaskets']
        }
        return parts_map.get(component, ['Various parts'])

class SchedulingAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(AgentType.SCHEDULING)
    
    def process(self, data: Dict) -> Dict:
        start_time = time.time()
        
        vehicle_info = data.get('vehicle_info', {})
        diagnoses = data.get('diagnoses', [])
        requires_immediate = data.get('requires_immediate_action', False)
        estimated_time = data.get('estimated_repair_time', 60)
        
        service_centers = get_all_service_centers()
        
        best_center = self._select_best_service_center(
            service_centers, 
            vehicle_info, 
            diagnoses,
            requires_immediate
        )
        
        booking_slot = self._find_optimal_slot(best_center, requires_immediate, estimated_time)
        
        priority = 'urgent' if requires_immediate else 'normal'
        service_type = self._determine_service_type(diagnoses)
        
        reasoning = f"Selected {best_center['name']} based on capacity ({best_center['current_load']}/{best_center['capacity']}), "
        reasoning += f"rating ({best_center['rating']}), and specializations. "
        reasoning += f"Scheduled for {booking_slot['date']} at {booking_slot['time']}."
        
        execution_time = time.time() - start_time
        
        result = {
            'service_center': best_center,
            'booking_slot': booking_slot,
            'priority': priority,
            'service_type': service_type,
            'estimated_duration': estimated_time,
            'booking_created': True
        }
        
        self.log_execution(
            action='schedule_service',
            input_data={'vehicle_id': vehicle_info.get('id'), 'urgent': requires_immediate},
            output_data={'center': best_center['name'], 'date': booking_slot['date']},
            reasoning=reasoning,
            execution_time=execution_time
        )
        
        return result
    
    def _select_best_service_center(self, centers: List[Dict], vehicle_info: Dict, diagnoses: List[Dict], urgent: bool) -> Dict:
        scored_centers = []
        
        vehicle_make = vehicle_info.get('make', '').lower()
        
        for center in centers:
            score = 0
            
            available_capacity = center['capacity'] - center['current_load']
            capacity_score = (available_capacity / center['capacity']) * 30
            score += capacity_score
            
            score += center['rating'] * 10
            
            specializations = json.loads(center.get('specializations', '[]')) if isinstance(center.get('specializations'), str) else center.get('specializations', [])
            
            if vehicle_make in [s.lower() for s in specializations]:
                score += 20
            if 'all' in [s.lower() for s in specializations]:
                score += 10
            
            for diag in diagnoses:
                component = diag.get('component', '').lower()
                if component in [s.lower() for s in specializations]:
                    score += 15
            
            if urgent and available_capacity > 2:
                score += 15
            
            scored_centers.append((center, score))
        
        scored_centers.sort(key=lambda x: x[1], reverse=True)
        
        return scored_centers[0][0] if scored_centers else centers[0]
    
    def _find_optimal_slot(self, center: Dict, urgent: bool, duration: int) -> Dict:
        if urgent:
            booking_date = datetime.now()
            if datetime.now().hour >= 17:
                booking_date = datetime.now() + timedelta(days=1)
            booking_time = "09:00"
        else:
            booking_date = datetime.now() + timedelta(days=random.randint(2, 5))
            hours = ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00']
            booking_time = random.choice(hours)
        
        return {
            'date': booking_date.strftime('%Y-%m-%d'),
            'time': booking_time,
            'duration_minutes': duration
        }
    
    def _determine_service_type(self, diagnoses: List[Dict]) -> str:
        if not diagnoses:
            return 'General Inspection'
        
        components = [d['component'] for d in diagnoses]
        
        if 'engine' in components or 'transmission' in components:
            return 'Major Service'
        elif 'brakes' in components or 'cooling_system' in components:
            return 'Safety Service'
        elif 'battery' in components:
            return 'Electrical Service'
        elif 'tires' in components:
            return 'Tire Service'
        else:
            return 'Diagnostic Service'

class CustomerAgent(BaseAgent):
    
    MESSAGE_TEMPLATES = {
        'alert_critical': """
Dear {customer_name},

URGENT: Your {vehicle_make} {vehicle_model} ({vin}) requires immediate attention.

Issue Detected: {issue_description}
Risk Level: CRITICAL
Recommended Action: {recommended_action}

We have automatically scheduled a service appointment for you:
Date: {booking_date}
Time: {booking_time}
Location: {service_center}

Please confirm this appointment by replying YES, or contact us to reschedule.

Safety First,
AutoSenseAI Team
        """,
        'alert_warning': """
Dear {customer_name},

Your {vehicle_make} {vehicle_model} requires attention soon.

Issue Detected: {issue_description}
Risk Level: WARNING
Recommended Action: {recommended_action}

We recommend scheduling a service within the next {days_until_issue} days.

Would you like us to book an appointment for you? Reply YES to confirm.

Best regards,
AutoSenseAI Team
        """,
        'booking_confirmation': """
Dear {customer_name},

Your service appointment has been confirmed!

Vehicle: {vehicle_make} {vehicle_model}
Date: {booking_date}
Time: {booking_time}
Location: {service_center}
Service Type: {service_type}
Estimated Duration: {duration} minutes

Please arrive 10 minutes before your scheduled time.

Thank you for choosing AutoSenseAI!
        """,
        'feedback_request': """
Dear {customer_name},

Thank you for visiting {service_center} for your {vehicle_make} {vehicle_model} service.

We'd love to hear about your experience! Please rate your service:
1 - Poor
2 - Fair
3 - Good
4 - Very Good
5 - Excellent

Your feedback helps us improve our service quality.

Thank you,
AutoSenseAI Team
        """
    }
    
    def __init__(self):
        super().__init__(AgentType.CUSTOMER)
    
    def process(self, data: Dict) -> Dict:
        start_time = time.time()
        
        action_type = data.get('action_type', 'notify')
        
        if action_type == 'send_alert':
            result = self._send_alert(data)
        elif action_type == 'confirm_booking':
            result = self._send_booking_confirmation(data)
        elif action_type == 'request_feedback':
            result = self._request_feedback(data)
        elif action_type == 'chat_response':
            result = self._generate_chat_response(data)
        else:
            result = {'status': 'unknown_action'}
        
        execution_time = time.time() - start_time
        
        self.log_execution(
            action=action_type,
            input_data={'customer': data.get('customer_name', 'Unknown')},
            output_data={'status': result.get('status', 'completed')},
            reasoning=result.get('reasoning', 'Customer communication processed'),
            execution_time=execution_time
        )
        
        return result
    
    def _send_alert(self, data: Dict) -> Dict:
        severity = data.get('severity', 'warning')
        template_key = f'alert_{severity}'
        template = self.MESSAGE_TEMPLATES.get(template_key, self.MESSAGE_TEMPLATES['alert_warning'])
        
        message = template.format(
            customer_name=data.get('customer_name', 'Valued Customer'),
            vehicle_make=data.get('vehicle_make', ''),
            vehicle_model=data.get('vehicle_model', ''),
            vin=data.get('vin', ''),
            issue_description=data.get('issue_description', 'Maintenance required'),
            recommended_action=data.get('recommended_action', 'Schedule service'),
            booking_date=data.get('booking_date', ''),
            booking_time=data.get('booking_time', ''),
            service_center=data.get('service_center', ''),
            days_until_issue=data.get('days_until_issue', 7)
        )
        
        return {
            'status': 'sent',
            'message': message,
            'channel': 'sms_email',
            'reasoning': f'Sent {severity} alert to customer about {data.get("issue_description", "issue")}'
        }
    
    def _send_booking_confirmation(self, data: Dict) -> Dict:
        template = self.MESSAGE_TEMPLATES['booking_confirmation']
        
        message = template.format(
            customer_name=data.get('customer_name', 'Valued Customer'),
            vehicle_make=data.get('vehicle_make', ''),
            vehicle_model=data.get('vehicle_model', ''),
            booking_date=data.get('booking_date', ''),
            booking_time=data.get('booking_time', ''),
            service_center=data.get('service_center', ''),
            service_type=data.get('service_type', 'General Service'),
            duration=data.get('duration', 60)
        )
        
        return {
            'status': 'sent',
            'message': message,
            'channel': 'sms_email',
            'reasoning': 'Booking confirmation sent successfully'
        }
    
    def _request_feedback(self, data: Dict) -> Dict:
        template = self.MESSAGE_TEMPLATES['feedback_request']
        
        message = template.format(
            customer_name=data.get('customer_name', 'Valued Customer'),
            vehicle_make=data.get('vehicle_make', ''),
            vehicle_model=data.get('vehicle_model', ''),
            service_center=data.get('service_center', '')
        )
        
        return {
            'status': 'sent',
            'message': message,
            'channel': 'sms_email',
            'reasoning': 'Feedback request sent to customer'
        }
    
    def _generate_chat_response(self, data: Dict) -> Dict:
        user_message = data.get('message', '').lower()
        vehicle_info = data.get('vehicle_info', {})
        
        if any(word in user_message for word in ['status', 'health', 'condition']):
            response = f"Your {vehicle_info.get('make', '')} {vehicle_info.get('model', '')} is currently in {vehicle_info.get('status', 'good')} condition with a health score of {vehicle_info.get('health_score', 85)}%."
        elif any(word in user_message for word in ['book', 'schedule', 'appointment']):
            response = "I can help you schedule a service appointment. Based on your vehicle's current condition, I recommend scheduling within the next week. Would you like me to find the best available slot?"
        elif any(word in user_message for word in ['alert', 'warning', 'issue']):
            response = "I see you have concerns about your vehicle. Let me check the latest diagnostics and get back to you with specific recommendations."
        elif any(word in user_message for word in ['cancel', 'reschedule']):
            response = "I understand you need to modify your appointment. Please provide your booking reference and preferred new date/time."
        elif any(word in user_message for word in ['thank', 'thanks']):
            response = "You're welcome! Is there anything else I can help you with regarding your vehicle?"
        else:
            response = "I'm here to help with your vehicle maintenance needs. You can ask me about your vehicle's health status, schedule service appointments, or get information about any alerts."
        
        return {
            'status': 'responded',
            'response': response,
            'reasoning': f'Generated contextual response to: "{user_message[:50]}..."'
        }

class RCAFeedbackAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(AgentType.RCA_FEEDBACK)
    
    def process(self, data: Dict) -> Dict:
        start_time = time.time()
        
        action_type = data.get('action_type', 'analyze')
        
        if action_type == 'analyze_failure':
            result = self._analyze_failure_pattern(data)
        elif action_type == 'generate_rca':
            result = self._generate_rca_report(data)
        elif action_type == 'aggregate_feedback':
            result = self._aggregate_feedback(data)
        else:
            result = {'status': 'unknown_action'}
        
        execution_time = time.time() - start_time
        
        self.log_execution(
            action=action_type,
            input_data={'type': action_type},
            output_data={'status': result.get('status', 'completed')},
            reasoning=result.get('reasoning', 'RCA analysis completed'),
            execution_time=execution_time
        )
        
        return result
    
    def _analyze_failure_pattern(self, data: Dict) -> Dict:
        component = data.get('component', 'unknown')
        failure_data = data.get('failure_data', [])
        
        pattern_analysis = {
            'component': component,
            'total_failures': len(failure_data),
            'common_symptoms': self._identify_common_symptoms(failure_data),
            'failure_conditions': self._identify_conditions(failure_data),
            'trend': 'increasing' if len(failure_data) > 5 else 'stable'
        }
        
        return {
            'status': 'analyzed',
            'analysis': pattern_analysis,
            'reasoning': f'Analyzed {len(failure_data)} failure instances for {component}'
        }
    
    def _generate_rca_report(self, data: Dict) -> Dict:
        component = data.get('component', 'unknown')
        pattern_analysis = data.get('pattern_analysis', {})
        
        root_causes = {
            'engine': ['Material fatigue', 'Manufacturing tolerance issue', 'Operating condition stress'],
            'battery': ['Charging system design', 'Heat management', 'Cell quality variation'],
            'brakes': ['Pad compound formulation', 'Caliper design', 'Usage pattern'],
            'cooling_system': ['Coolant flow design', 'Thermostat calibration', 'Hose material'],
            'tires': ['Compound mixture', 'Structural design', 'Pressure monitoring'],
            'transmission': ['Gear material', 'Lubrication system', 'Electronic control']
        }
        
        recommendations = {
            'engine': 'Review material specifications and heat treatment process',
            'battery': 'Evaluate thermal management system and charging protocols',
            'brakes': 'Test alternative pad compounds and review caliper tolerances',
            'cooling_system': 'Analyze coolant flow patterns and component specifications',
            'tires': 'Review compound formulation and manufacturing process',
            'transmission': 'Examine gear cutting process and lubrication system design'
        }
        
        rca_report = {
            'component': component,
            'failure_pattern': pattern_analysis.get('common_symptoms', ['Unknown']),
            'root_cause': random.choice(root_causes.get(component, ['Design review needed'])),
            'affected_vehicles': pattern_analysis.get('total_failures', 0),
            'severity': 'high' if pattern_analysis.get('trend') == 'increasing' else 'medium',
            'recommendation': recommendations.get(component, 'Conduct detailed engineering review'),
            'oem_action_required': pattern_analysis.get('total_failures', 0) > 3
        }
        
        if rca_report['oem_action_required']:
            create_rca_report(
                component=rca_report['component'],
                failure_pattern=str(rca_report['failure_pattern']),
                root_cause=rca_report['root_cause'],
                affected_vehicles=rca_report['affected_vehicles'],
                severity=rca_report['severity'],
                recommendation=rca_report['recommendation'],
                oem_action_required=1
            )
        
        return {
            'status': 'generated',
            'rca_report': rca_report,
            'reasoning': f'Generated RCA for {component}. OEM notification: {"Required" if rca_report["oem_action_required"] else "Not required"}'
        }
    
    def _aggregate_feedback(self, data: Dict) -> Dict:
        feedback_list = data.get('feedback', [])
        
        if not feedback_list:
            return {
                'status': 'no_data',
                'summary': {},
                'reasoning': 'No feedback data to aggregate'
            }
        
        total = len(feedback_list)
        avg_rating = sum(f.get('rating', 3) for f in feedback_list) / total
        resolved_count = sum(1 for f in feedback_list if f.get('issue_resolved', True))
        
        summary = {
            'total_feedback': total,
            'average_rating': round(avg_rating, 1),
            'resolution_rate': round(resolved_count / total * 100, 1),
            'common_issues': self._extract_common_issues(feedback_list),
            'improvement_areas': self._identify_improvements(feedback_list)
        }
        
        return {
            'status': 'aggregated',
            'summary': summary,
            'reasoning': f'Aggregated {total} feedback entries. Avg rating: {avg_rating:.1f}'
        }
    
    def _identify_common_symptoms(self, failure_data: List[Dict]) -> List[str]:
        return ['Unusual noise', 'Performance degradation', 'Warning light activation']
    
    def _identify_conditions(self, failure_data: List[Dict]) -> List[str]:
        return ['High mileage', 'Extreme temperature operation', 'Heavy load conditions']
    
    def _extract_common_issues(self, feedback_list: List[Dict]) -> List[str]:
        return ['Wait time', 'Parts availability', 'Communication']
    
    def _identify_improvements(self, feedback_list: List[Dict]) -> List[str]:
        return ['Faster service', 'Better updates', 'More convenient scheduling']

class MasterAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(AgentType.MASTER)
        self.prediction_agent = PredictionAgent()
        self.diagnosis_agent = DiagnosisAgent()
        self.scheduling_agent = SchedulingAgent()
        self.customer_agent = CustomerAgent()
        self.rca_agent = RCAFeedbackAgent()
    
    def orchestrate(self, telemetry: Dict, vehicle_info: Dict) -> Dict:
        start_time = time.time()
        workflow_results = {
            'vehicle_id': vehicle_info.get('id'),
            'timestamp': datetime.now().isoformat(),
            'stages': []
        }
        
        prediction_result = self.prediction_agent.process({
            'telemetry': telemetry,
            'vehicle_info': vehicle_info
        })
        workflow_results['stages'].append({
            'agent': 'prediction',
            'result': prediction_result
        })
        
        diagnosis_result = None
        if prediction_result.get('requires_diagnosis'):
            diagnosis_result = self.diagnosis_agent.process({
                'prediction_report': prediction_result['prediction_report'],
                'vehicle_info': vehicle_info
            })
            workflow_results['stages'].append({
                'agent': 'diagnosis',
                'result': diagnosis_result
            })
        
        scheduling_result = None
        if prediction_result.get('requires_scheduling') and diagnosis_result:
            scheduling_result = self.scheduling_agent.process({
                'vehicle_info': vehicle_info,
                'diagnoses': diagnosis_result['diagnoses'],
                'requires_immediate_action': diagnosis_result['requires_immediate_action'],
                'estimated_repair_time': diagnosis_result['estimated_repair_time']
            })
            workflow_results['stages'].append({
                'agent': 'scheduling',
                'result': scheduling_result
            })
        
        if scheduling_result and scheduling_result.get('booking_created'):
            severity = 'critical' if diagnosis_result['requires_immediate_action'] else 'warning'
            top_diagnosis = diagnosis_result['diagnoses'][0] if diagnosis_result['diagnoses'] else {}
            
            customer_result = self.customer_agent.process({
                'action_type': 'send_alert',
                'severity': severity,
                'customer_name': vehicle_info.get('owner_name', 'Customer'),
                'vehicle_make': vehicle_info.get('make', ''),
                'vehicle_model': vehicle_info.get('model', ''),
                'vin': vehicle_info.get('vin', ''),
                'issue_description': top_diagnosis.get('primary_cause', 'Maintenance required'),
                'recommended_action': top_diagnosis.get('recommended_actions', ['Service needed'])[0] if top_diagnosis.get('recommended_actions') else 'Service needed',
                'booking_date': scheduling_result['booking_slot']['date'],
                'booking_time': scheduling_result['booking_slot']['time'],
                'service_center': scheduling_result['service_center']['name']
            })
            workflow_results['stages'].append({
                'agent': 'customer',
                'result': customer_result
            })
        
        health_score = prediction_result['prediction_report']['overall_health_score']
        if health_score < 50:
            status = 'critical'
        elif health_score < 70:
            status = 'warning'
        else:
            status = 'healthy'
        
        update_vehicle_health(vehicle_info['id'], health_score, status)
        
        for alert_data in prediction_result.get('alerts_to_create', []):
            create_alert(
                vehicle_id=vehicle_info['id'],
                alert_type='predictive',
                severity=alert_data['severity'],
                component=alert_data['component'],
                description=alert_data['action'],
                failure_probability=prediction_result['prediction_report']['failure_prediction']['failure_probability'],
                predicted_failure_date=prediction_result['prediction_report']['component_health'].get(alert_data['component'], {}).get('predicted_failure_date')
            )
        
        if scheduling_result:
            create_booking(
                vehicle_id=vehicle_info['id'],
                service_center_id=scheduling_result['service_center']['id'],
                alert_id=None,
                booking_date=scheduling_result['booking_slot']['date'],
                booking_time=scheduling_result['booking_slot']['time'],
                service_type=scheduling_result['service_type'],
                priority=scheduling_result['priority'],
                estimated_duration=scheduling_result['estimated_duration']
            )
        
        execution_time = time.time() - start_time
        
        workflow_results['total_execution_time'] = round(execution_time, 3)
        workflow_results['actions_taken'] = len(workflow_results['stages'])
        workflow_results['health_score'] = health_score
        workflow_results['status'] = status
        
        reasoning = f"Orchestrated {len(workflow_results['stages'])} agents. "
        reasoning += f"Vehicle health: {health_score}% ({status}). "
        if scheduling_result:
            reasoning += f"Service scheduled at {scheduling_result['service_center']['name']}."
        
        self.log_execution(
            action='orchestrate_workflow',
            input_data={'vehicle_id': vehicle_info['id']},
            output_data={'stages': len(workflow_results['stages']), 'health': health_score},
            reasoning=reasoning,
            execution_time=execution_time
        )
        
        return workflow_results

def get_master_agent() -> MasterAgent:
    return MasterAgent()
