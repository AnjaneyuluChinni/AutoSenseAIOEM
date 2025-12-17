import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time
import math

# Update the imports in app.py to include the new functions

# Update the imports in app.py - remove problematic ones
from database import (
    init_database, seed_sample_data, get_all_vehicles, get_vehicle_by_id,
    get_all_alerts, get_all_service_centers, get_all_bookings, get_all_feedback,
    get_dashboard_stats, get_agent_logs, get_rca_reports, update_booking_status,
    create_feedback, get_telemetry_history, save_telemetry,
    # Add new functions
    get_nearby_garages, get_parts_catalog, create_breakdown_incident,
    update_breakdown_estimate, get_breakdown_history, seed_additional_data,
    create_booking,
    # Keep only these garage functions that actually exist
    get_garage_by_id, update_garage_load,get_all_garages,  # Add this
    get_breakdowns_for_garage,  # Add this
    update_breakdown_status,  # Add this
    update_breakdown_estimate,  # Add this
    update_garage_load,  # Add this
    get_garage_by_id,
)
from telemetry import TelemetrySimulator, generate_fleet_telemetry, analyze_telemetry_anomalies
from predictive_engine import get_prediction_engine
from agents import get_master_agent, CustomerAgent

st.set_page_config(
    page_title="AutoSenseAI - Predictive Maintenance Platform",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1e3a5f, #2d5a87);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .status-critical {
        background-color: #ff4444;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .status-warning {
        background-color: #ffbb33;
        color: black;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .status-healthy {
        background-color: #00C851;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .agent-log {
        background-color: #f0f2f6;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.25rem 0;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .garage-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
    }
    .part-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #00C851;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_app():
    init_database()
    seed_sample_data()
    seed_additional_data()  # Seed garages and parts data
    return True

initialize_app()

def render_oem_dashboard():
    st.markdown("## OEM Analytics Dashboard")
    
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.markdown("### Fleet Monitoring & Analytics")
    with col_header2:
        if st.button("Run Fleet Analysis", type="primary", use_container_width=True):
            with st.spinner("Running multi-agent analysis on all vehicles..."):
                vehicles = get_all_vehicles()
                master_agent = get_master_agent()
                results = []
                progress = st.progress(0)
                
                for i, vehicle in enumerate(vehicles):
                    scenario = 'random'
                    simulator = TelemetrySimulator(vehicle['id'], scenario)
                    telemetry = simulator.generate_telemetry()
                    save_telemetry(vehicle['id'], telemetry)
                    
                    result = master_agent.orchestrate(telemetry, vehicle)
                    results.append(result)
                    progress.progress((i + 1) / len(vehicles))
                
                critical_count = sum(1 for r in results if r['status'] == 'critical')
                warning_count = sum(1 for r in results if r['status'] == 'warning')
                
                st.success(f"Fleet analysis complete! Analyzed {len(vehicles)} vehicles. Found {critical_count} critical and {warning_count} warning issues.")
                st.rerun()
    
    stats = get_dashboard_stats()
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Vehicles", stats['total_vehicles'], delta=None)
    with col2:
        st.metric("Active Alerts", stats['active_alerts'], delta=None, delta_color="inverse")
    with col3:
        st.metric("Pending Bookings", stats['pending_bookings'])
    with col4:
        st.metric("Completed Services", stats['completed_services'])
    with col5:
        st.metric("Avg Rating", f"{stats['avg_rating']}/5")
    with col6:
        st.metric("Critical Vehicles", stats['critical_vehicles'], delta_color="inverse")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Fleet Health Overview")
        vehicles = get_all_vehicles()
        if vehicles:
            health_data = pd.DataFrame(vehicles)
            
            status_counts = health_data['status'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Vehicle Status Distribution",
                color=status_counts.index,
                color_discrete_map={
                    'healthy': '#00C851',
                    'warning': '#ffbb33',
                    'critical': '#ff4444'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Health Score Distribution")
        if vehicles:
            fig = px.histogram(
                health_data,
                x='health_score',
                nbins=20,
                title="Vehicle Health Scores",
                color_discrete_sequence=['#667eea']
            )
            fig.update_layout(xaxis_title="Health Score (%)", yaxis_title="Number of Vehicles")
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("### Active Alerts")
    alerts = get_all_alerts('active')
    if alerts:
        alerts_df = pd.DataFrame(alerts)
        display_cols = ['vin', 'make', 'model', 'component', 'severity', 'description', 'failure_probability', 'created_at']
        available_cols = [c for c in display_cols if c in alerts_df.columns]
        st.dataframe(alerts_df[available_cols], use_container_width=True)
    else:
        st.info("No active alerts at this time.")
    
    st.markdown("### RCA Reports for Manufacturing")
    rca_reports = get_rca_reports()
    if rca_reports:
        rca_df = pd.DataFrame(rca_reports)
        st.dataframe(rca_df, use_container_width=True)
    else:
        st.info("No RCA reports generated yet.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Component Failure Trends")
        if alerts:
            component_counts = pd.DataFrame(alerts)['component'].value_counts()
            fig = px.bar(
                x=component_counts.index,
                y=component_counts.values,
                title="Alerts by Component",
                labels={'x': 'Component', 'y': 'Number of Alerts'},
                color=component_counts.values,
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Severity Distribution")
        if alerts:
            severity_counts = pd.DataFrame(alerts)['severity'].value_counts()
            fig = px.bar(
                x=severity_counts.index,
                y=severity_counts.values,
                title="Alerts by Severity",
                labels={'x': 'Severity', 'y': 'Count'},
                color=severity_counts.index,
                color_discrete_map={
                    'critical': '#ff4444',
                    'warning': '#ffbb33',
                    'info': '#33b5e5'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

def render_service_center_view():
    st.markdown("## Service Center Management")
    
    service_centers = get_all_service_centers()
    
    st.markdown("### Service Center Overview")
    cols = st.columns(len(service_centers))
    for i, center in enumerate(service_centers):
        with cols[i]:
            utilization = (center['current_load'] / center['capacity']) * 100
            color = "normal" if utilization < 70 else "inverse" if utilization > 90 else "off"
            st.metric(
                center['name'][:20],
                f"{center['current_load']}/{center['capacity']}",
                f"{utilization:.0f}% utilized",
                delta_color=color
            )
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["Scheduled Bookings", "In Progress", "Completed"])
    
    with tab1:
        scheduled = get_all_bookings('scheduled')
        if scheduled:
            for booking in scheduled:
                with st.expander(f"📅 {booking['booking_date']} {booking['booking_time']} - {booking['make']} {booking['model']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Customer:** {booking['owner_name']}")
                        st.write(f"**Phone:** {booking['owner_phone']}")
                    with col2:
                        st.write(f"**Service Type:** {booking['service_type']}")
                        st.write(f"**Priority:** {booking['priority']}")
                    with col3:
                        st.write(f"**Duration:** {booking['estimated_duration']} min")
                        st.write(f"**Location:** {booking['service_center_name']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Start Service", key=f"start_{booking['id']}"):
                            update_booking_status(booking['id'], 'in_progress')
                            st.success("Service started!")
                            st.rerun()
                    with col2:
                        if st.button("Cancel", key=f"cancel_{booking['id']}"):
                            update_booking_status(booking['id'], 'cancelled')
                            st.warning("Booking cancelled")
                            st.rerun()
        else:
            st.info("No scheduled bookings.")
    
    with tab2:
        in_progress = get_all_bookings('in_progress')
        if in_progress:
            for booking in in_progress:
                with st.expander(f"🔧 {booking['make']} {booking['model']} - {booking['service_type']}"):
                    st.write(f"**Customer:** {booking['owner_name']}")
                    st.write(f"**Started:** {booking['booking_date']} {booking['booking_time']}")
                    
                    notes = st.text_area("Technician Notes", key=f"notes_{booking['id']}")
                    
                    if st.button("Complete Service", key=f"complete_{booking['id']}"):
                        update_booking_status(booking['id'], 'completed', notes)
                        st.success("Service completed!")
                        st.rerun()
        else:
            st.info("No services in progress.")
    
    with tab3:
        completed = get_all_bookings('completed')
        if completed:
            completed_df = pd.DataFrame(completed)
            display_cols = ['booking_date', 'make', 'model', 'owner_name', 'service_type', 'completed_at']
            available_cols = [c for c in display_cols if c in completed_df.columns]
            st.dataframe(completed_df[available_cols], use_container_width=True)
        else:
            st.info("No completed services yet.")

def render_vehicle_owner_portal():
    st.markdown("## Vehicle Owner Portal")
    
    vehicles = get_all_vehicles()
    
    if not vehicles:
        st.warning("No vehicles registered.")
        return
    
    vehicle_options = {f"{v['make']} {v['model']} ({v['vin']})": v['id'] for v in vehicles}
    selected_vehicle_name = st.selectbox("Select Your Vehicle", list(vehicle_options.keys()))
    selected_vehicle_id = vehicle_options[selected_vehicle_name]
    vehicle = get_vehicle_by_id(selected_vehicle_id)
    
    if not vehicle:
        st.error("Vehicle not found.")
        return
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown("### Vehicle Details")
        st.write(f"**Make:** {vehicle['make']}")
        st.write(f"**Model:** {vehicle['model']}")
        st.write(f"**Year:** {vehicle['year']}")
        st.write(f"**VIN:** {vehicle['vin']}")
        st.write(f"**Mileage:** {vehicle['mileage']:,} km")
        st.write(f"**Last Service:** {vehicle['last_service_date']}")
    
    with col2:
        st.markdown("### Health Status")
        
        health_score = vehicle['health_score']
        status = vehicle['status']
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=health_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Vehicle Health Score"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "#667eea"},
                'steps': [
                    {'range': [0, 50], 'color': "#ffcccb"},
                    {'range': [50, 70], 'color': "#ffffcc"},
                    {'range': [70, 100], 'color': "#ccffcc"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': health_score
                }
            }
        ))
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
        
        status_class = f"status-{status}"
        st.markdown(f"<p>Current Status: <span class='{status_class}'>{status.upper()}</span></p>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("### Quick Actions")
        
        if st.button("🔄 Run Diagnostics", use_container_width=True):
            with st.spinner("Running diagnostics..."):
                simulator = TelemetrySimulator(selected_vehicle_id, 'random')
                telemetry = simulator.generate_telemetry()
                save_telemetry(selected_vehicle_id, telemetry)
                
                master_agent = get_master_agent()
                result = master_agent.orchestrate(telemetry, vehicle)
                
                st.session_state['last_diagnostic'] = result
                st.success("Diagnostics complete!")
                st.rerun()
        
        if st.button("📅 Book Service", use_container_width=True):
            st.session_state['show_booking'] = True
        
        if st.button("💬 Chat with AI", use_container_width=True):
            st.session_state['show_chat'] = True
    
    if st.session_state.get('last_diagnostic'):
        st.markdown("### Latest Diagnostic Results")
        result = st.session_state['last_diagnostic']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Health Score:** {result['health_score']}%")
            st.write(f"**Status:** {result['status']}")
            st.write(f"**Agents Used:** {result['actions_taken']}")
        
        with col2:
            st.write(f"**Execution Time:** {result['total_execution_time']:.2f}s")
            for stage in result['stages']:
                st.write(f"✓ {stage['agent'].title()} Agent completed")
    
    if st.session_state.get('show_booking'):
        st.markdown("### Book Service Appointment")
        service_centers = get_all_service_centers()
        
        col1, col2 = st.columns(2)
        with col1:
            center_options = {c['name']: c['id'] for c in service_centers}
            selected_center = st.selectbox("Select Service Center", list(center_options.keys()))
            service_date = st.date_input("Preferred Date", min_value=datetime.now().date())
        
        with col2:
            service_time = st.selectbox("Preferred Time", ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"])
            service_type = st.selectbox("Service Type", ["General Service", "Diagnostic Check", "Brake Service", "Engine Tune-up", "Tire Service"])
        
        if st.button("Confirm Booking"):
            create_booking(
                vehicle_id=selected_vehicle_id,
                service_center_id=center_options[selected_center],
                alert_id=None,
                booking_date=service_date.strftime('%Y-%m-%d'),
                booking_time=service_time,
                service_type=service_type,
                priority='normal',
                estimated_duration=60
            )
            st.success(f"Booking confirmed for {service_date} at {service_time}!")
            st.session_state['show_booking'] = False
            st.rerun()
    
    if st.session_state.get('show_chat'):
        st.markdown("### Chat with AutoSenseAI")
        
        if 'chat_history' not in st.session_state:
            st.session_state['chat_history'] = []
        
        for msg in st.session_state['chat_history']:
            if msg['role'] == 'user':
                st.chat_message("user").write(msg['content'])
            else:
                st.chat_message("assistant").write(msg['content'])
        
        user_input = st.chat_input("Ask about your vehicle...")
        
        if user_input:
            st.session_state['chat_history'].append({'role': 'user', 'content': user_input})
            
            customer_agent = CustomerAgent()
            response = customer_agent.process({
                'action_type': 'chat_response',
                'message': user_input,
                'vehicle_info': vehicle
            })
            
            st.session_state['chat_history'].append({'role': 'assistant', 'content': response['response']})
            st.rerun()
    
    st.markdown("### Your Bookings")
    all_bookings = get_all_bookings()
    vehicle_bookings = [b for b in all_bookings if b['vehicle_id'] == selected_vehicle_id]
    
    if vehicle_bookings:
        for booking in vehicle_bookings[:5]:
            status_icon = "📅" if booking['status'] == 'scheduled' else "🔧" if booking['status'] == 'in_progress' else "✅"
            st.write(f"{status_icon} {booking['booking_date']} - {booking['service_type']} at {booking['service_center_name']} ({booking['status']})")
    else:
        st.info("No bookings found for this vehicle.")

def render_telemetry_simulator():
    st.markdown("## Telemetry Simulator")
    
    vehicles = get_all_vehicles()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### Simulation Settings")
        
        vehicle_options = {f"{v['make']} {v['model']}": v['id'] for v in vehicles}
        selected_vehicle_name = st.selectbox("Select Vehicle", list(vehicle_options.keys()), key="sim_vehicle")
        selected_vehicle_id = vehicle_options[selected_vehicle_name]
        
        scenario = st.selectbox("Scenario", ["normal", "degrading", "critical", "random"])
        
        if st.button("Generate Single Reading", use_container_width=True):
            simulator = TelemetrySimulator(selected_vehicle_id, scenario)
            telemetry = simulator.generate_telemetry()
            st.session_state['current_telemetry'] = telemetry
            save_telemetry(selected_vehicle_id, telemetry)
            st.success("Telemetry generated!")
        
        if st.button("Run Full Analysis", use_container_width=True):
            with st.spinner("Running multi-agent analysis..."):
                simulator = TelemetrySimulator(selected_vehicle_id, scenario)
                telemetry = simulator.generate_telemetry()
                save_telemetry(selected_vehicle_id, telemetry)
                
                vehicle = get_vehicle_by_id(selected_vehicle_id)
                master_agent = get_master_agent()
                result = master_agent.orchestrate(telemetry, vehicle)
                
                st.session_state['analysis_result'] = result
                st.session_state['current_telemetry'] = telemetry
            st.success("Analysis complete!")
    
    with col2:
        if st.session_state.get('current_telemetry'):
            st.markdown("### Current Telemetry Reading")
            telemetry = st.session_state['current_telemetry']
            
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                st.metric("Engine Temp", f"{telemetry['engine_temp']}°C")
                st.metric("Oil Pressure", f"{telemetry['oil_pressure']} PSI")
                st.metric("Battery", f"{telemetry['battery_voltage']} V")
            
            with col_b:
                st.metric("RPM", telemetry['rpm'])
                st.metric("Speed", f"{telemetry['speed']} km/h")
                st.metric("Vibration", f"{telemetry['vibration_level']}")
            
            with col_c:
                st.metric("Brake Wear", f"{telemetry['brake_wear']}%")
                st.metric("Fuel Level", f"{telemetry['fuel_level']}%")
                st.metric("Coolant Temp", f"{telemetry['coolant_temp']}°C")
            
            st.markdown("#### Tire Pressures (PSI)")
            tire_col1, tire_col2 = st.columns(2)
            with tire_col1:
                st.write(f"FL: {telemetry['tire_pressure_fl']} | FR: {telemetry['tire_pressure_fr']}")
            with tire_col2:
                st.write(f"RL: {telemetry['tire_pressure_rl']} | RR: {telemetry['tire_pressure_rr']}")
            
            if telemetry.get('error_codes'):
                st.warning(f"Error Codes: {', '.join(telemetry['error_codes'])}")
    
    if st.session_state.get('analysis_result'):
        st.markdown("---")
        st.markdown("### Multi-Agent Analysis Results")
        
        result = st.session_state['analysis_result']
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Health Score", f"{result['health_score']}%")
        with col2:
            st.metric("Status", result['status'].upper())
        with col3:
            st.metric("Agents Used", result['actions_taken'])
        with col4:
            st.metric("Time", f"{result['total_execution_time']:.2f}s")
        
        st.markdown("#### Agent Workflow")
        for stage in result['stages']:
            agent_name = stage['agent'].title()
            with st.expander(f"🤖 {agent_name} Agent"):
                st.json(stage['result'])

def render_agent_logs():
    st.markdown("## Agent Activity Logs")
    
    logs = get_agent_logs(100)
    
    if not logs:
        st.info("No agent activity recorded yet. Run a diagnostic to see agent logs.")
        return
    
    agent_filter = st.multiselect(
        "Filter by Agent",
        ["master_agent", "prediction_agent", "diagnosis_agent", "scheduling_agent", "customer_agent", "rca_feedback_agent"],
        default=[]
    )
    
    filtered_logs = logs if not agent_filter else [l for l in logs if l['agent_name'] in agent_filter]
    
    for log in filtered_logs:
        status_icon = "✅" if log['status'] == 'success' else "❌"
        
        with st.expander(f"{status_icon} {log['agent_name']} - {log['action']} ({log['created_at'][:19]})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Execution Time:** {log['execution_time']:.4f}s")
                st.write(f"**Status:** {log['status']}")
            
            with col2:
                st.write(f"**Reasoning:** {log['decision_reasoning']}")
            
            if log['input_data']:
                st.write("**Input:**")
                try:
                    st.json(json.loads(log['input_data']))
                except:
                    st.write(log['input_data'])
            
            if log['output_data']:
                st.write("**Output:**")
                try:
                    st.json(json.loads(log['output_data']))
                except:
                    st.write(log['output_data'])

def render_breakdown_assistance():
    st.markdown("## 🚨 Breakdown Assistance")
    
    vehicles = get_all_vehicles()
    if not vehicles:
        st.warning("No vehicles registered.")
        return
    
    vehicle_options = {f"{v['make']} {v['model']} ({v['vin']})": v['id'] for v in vehicles}
    selected_vehicle_name = st.selectbox("Select Your Vehicle", list(vehicle_options.keys()), key="breakdown_vehicle")
    selected_vehicle_id = vehicle_options[selected_vehicle_name]
    vehicle = get_vehicle_by_id(selected_vehicle_id)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Report Breakdown")
        
        breakdown_type = st.selectbox(
            "Breakdown Type",
            ["Engine Failure", "Battery Dead", "Flat Tire", "Accident", "Overheating", 
             "Electrical Failure", "Fuel System", "Brake Failure", "Other"]
        )
        
        st.markdown("#### 📍 Enter Your Location")
        
        # City selection for simplified location
        city = st.selectbox(
            "Select City",
            ["Mumbai", "Delhi", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune"]
        )
        
        # Predefined coordinates for major cities
        city_coordinates = {
            "Mumbai": (19.0760, 72.8777),
            "Delhi": (28.7041, 77.1025),
            "Bangalore": (12.9716, 77.5946),
            "Chennai": (13.0827, 80.2707),
            "Kolkata": (22.5726, 88.3639),
            "Hyderabad": (17.3850, 78.4867),
            "Pune": (18.5204, 73.8567)
        }
        
        latitude, longitude = city_coordinates.get(city, (19.0760, 72.8777))
        
        st.info(f"📍 Selected: {city} ({latitude:.4f}, {longitude:.4f})")
        
        # Manual coordinate override
        use_custom = st.checkbox("Enter custom coordinates")
        if use_custom:
            col_lat, col_lng = st.columns(2)
            with col_lat:
                latitude = st.number_input("Latitude", value=latitude, format="%.6f")
            with col_lng:
                longitude = st.number_input("Longitude", value=longitude, format="%.6f")
        
        additional_info = st.text_area("Additional Information (Symptoms, noises, etc.)")
        
        if st.button("🚨 Request Assistance", type="primary", use_container_width=True):
            incident_id = create_breakdown_incident(
                vehicle_id=selected_vehicle_id,
                breakdown_type=breakdown_type,
                latitude=latitude,
                longitude=longitude
            )
            
            st.session_state['breakdown_location'] = (latitude, longitude)
            st.session_state['breakdown_incident_id'] = incident_id
            st.session_state['breakdown_city'] = city
            st.success(f"Breakdown reported! Incident ID: #{incident_id}")
    
    with col2:
        if 'breakdown_location' in st.session_state:
            st.markdown("### Nearby Garages")
            latitude, longitude = st.session_state['breakdown_location']
            city = st.session_state.get('breakdown_city', 'Mumbai')
            
            garages = get_nearby_garages(latitude, longitude, radius_km=20)
            
            if garages:
                st.info(f"Found {len(garages)} garages within 20km of {city}")
                
                for garage in garages:
                    with st.expander(f"🏢 {garage['name']} ({garage['distance_km']:.1f} km)", expanded=False):
                        st.markdown(f"""
                        <div class="garage-card">
                            <p><strong>📍 Address:</strong> {garage['address']}</p>
                            <p><strong>📞 Phone:</strong> {garage['phone']}</p>
                            <p><strong>⭐ Rating:</strong> {garage['rating']}/5</p>
                            <p><strong>🔧 Specialization:</strong> {garage['specialization']}</p>
                            <p><strong>⏱️ Response Time:</strong> {garage['estimated_response_time']} mins</p>
                            <p><strong>📊 Current Load:</strong> {garage['current_load']}/{garage['capacity']}</p>
                            <p><strong>🕒 Operating Hours:</strong> {garage['operating_hours']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Calculate estimated total time
                        estimated_total_time = garage['estimated_response_time'] + 60  # 60 mins for repair
                        
                        if st.button(f"Select This Garage (Est. {estimated_total_time} mins)", 
                                   key=f"select_{garage['id']}", 
                                   use_container_width=True):
                            update_breakdown_estimate(
                                incident_id=st.session_state['breakdown_incident_id'],
                                estimated_fix_time=estimated_total_time,
                                garage_id=garage['id']
                            )
                            st.success(f"✅ Garage {garage['name']} assigned! Estimated fix time: {estimated_total_time} minutes")
                            st.balloons()
            else:
                st.warning("No garages found nearby. Here are emergency options:")
                
                emergency_garages = [
                    {"name": "National Roadside Assistance", "phone": "1800-123-4567", "response": "30 mins"},
                    {"name": "Emergency Towing Service", "phone": "1800-987-6543", "response": "45 mins"},
                    {"name": "24x7 Mechanic Helpline", "phone": "1800-555-7890", "response": "60 mins"}
                ]
                
                for egarage in emergency_garages:
                    with st.container():
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.write(f"**{egarage['name']}**")
                            st.write(f"Phone: {egarage['phone']}")
                        with col_b:
                            if st.button("Call", key=f"call_{egarage['name']}"):
                                st.info(f"Calling {egarage['name']} at {egarage['phone']}")
                
                if st.button("📞 Call Police (100)", use_container_width=True):
                    st.warning("Police notified. Please stay in your vehicle until help arrives.")
        
        # Show breakdown history
        st.markdown("### 📋 Breakdown History")
        breakdowns = get_breakdown_history(selected_vehicle_id)
        
        if breakdowns:
            for bd in breakdowns[:3]:  # Show last 3 breakdowns
                status_color = {
                    'reported': 'orange',
                    'assigned': 'blue',
                    'in_progress': 'purple',
                    'completed': 'green',
                    'cancelled': 'red'
                }.get(bd['status'], 'gray')
                
                st.markdown(f"""
                <div style="border-left: 4px solid {status_color}; padding-left: 10px; margin: 10px 0;">
                    <p><strong>{bd['breakdown_type']}</strong> - {bd['reported_at'][:16]}</p>
                    <p>Status: <span style="color: {status_color}; font-weight: bold">{bd['status'].replace('_', ' ').title()}</span></p>
                    {f"<p>Garage: {bd.get('garage_name', 'Not assigned')}</p>" if bd.get('garage_name') else ""}
                    {f"<p>Est. Fix Time: {bd.get('estimated_fix_time', 'N/A')} mins</p>" if bd.get('estimated_fix_time') else ""}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No breakdown history for this vehicle.")

def render_parts_catalog():
    st.markdown("## 🔧 Parts Catalog & Pricing")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        make_filter = st.selectbox("Vehicle Make", ["All", "Hero", "Mahindra"])
    with col2:
        category_filter = st.selectbox("Category", ["All", "Engine", "Electrical", "Brakes", 
                                                   "Tires", "Suspension", "Cooling"])
    with col3:
        sort_by = st.selectbox("Sort By", ["Price (Low to High)", "Price (High to Low)", 
                                          "Name", "Stock", "Lead Time"])
    
    make = None if make_filter == "All" else make_filter
    category = None if category_filter == "All" else category_filter
    
    parts = get_parts_catalog(make=make, category=category)
    
    if parts:
        parts_df = pd.DataFrame(parts)
        
        # Apply sorting
        if sort_by == "Price (Low to High)":
            parts_df = parts_df.sort_values('oem_price')
        elif sort_by == "Price (High to Low)":
            parts_df = parts_df.sort_values('oem_price', ascending=False)
        elif sort_by == "Name":
            parts_df = parts_df.sort_values('part_name')
        elif sort_by == "Stock":
            parts_df = parts_df.sort_values('stock_quantity', ascending=False)
        elif sort_by == "Lead Time":
            parts_df = parts_df.sort_values('lead_time_days')
        
        st.markdown(f"### 📦 Found {len(parts)} Parts")
        
        # Data to Visualization Feature
        st.markdown("#### 📊 Convert Tabular Data to Visualization")
        
        with st.expander("Chart Settings", expanded=True):
            col_v1, col_v2, col_v3 = st.columns(3)
            with col_v1:
                chart_type = st.selectbox("Chart Type", ["Bar Chart", "Pie Chart", "Line Chart", "Scatter Plot"])
            with col_v2:
                available_columns = parts_df.select_dtypes(include=['number']).columns.tolist()
                x_axis = st.selectbox("X-Axis", parts_df.columns.tolist(), 
                                     index=parts_df.columns.tolist().index('part_name') if 'part_name' in parts_df.columns else 0)
            with col_v3:
                y_axis = st.selectbox("Y-Axis", available_columns, 
                                     index=available_columns.index('oem_price') if 'oem_price' in available_columns else 0)
        
        if st.button("🔄 Generate Chart", type="secondary"):
            st.markdown("### 📈 Visualization Output")
            
            try:
                if chart_type == "Bar Chart":
                    fig = px.bar(parts_df.head(20), x=x_axis, y=y_axis, 
                                title=f"{y_axis} by {x_axis} (Top 20)",
                                color=y_axis, color_continuous_scale='Viridis',
                                hover_data=parts_df.columns.tolist())
                    fig.update_xaxes(tickangle=45)
                    
                elif chart_type == "Pie Chart":
                    fig = px.pie(parts_df.head(10), names=x_axis, values=y_axis, 
                                title=f"Distribution of {y_axis} by {x_axis} (Top 10)",
                                hole=0.3)
                    
                elif chart_type == "Line Chart":
                    parts_sorted = parts_df.sort_values(x_axis) if parts_df[x_axis].dtype in ['int64', 'float64'] else parts_df
                    fig = px.line(parts_sorted.head(15), x=x_axis, y=y_axis, 
                                 title=f"{y_axis} Trend by {x_axis}",
                                 markers=True)
                    
                elif chart_type == "Scatter Plot":
                    size_col = 'stock_quantity' if 'stock_quantity' in parts_df.columns else y_axis
                    fig = px.scatter(parts_df, x=x_axis, y=y_axis, 
                                    size=size_col, color=y_axis,
                                    title=f"{y_axis} vs {x_axis}",
                                    hover_data=parts_df.columns.tolist(),
                                    size_max=30)
                
                fig.update_layout(height=500, hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
                
                # Chart statistics
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                with col_stats1:
                    st.metric(f"Avg {y_axis}", f"₹{parts_df[y_axis].mean():.2f}")
                with col_stats2:
                    st.metric(f"Min {y_axis}", f"₹{parts_df[y_axis].min():.2f}")
                with col_stats3:
                    st.metric(f"Max {y_axis}", f"₹{parts_df[y_axis].max():.2f}")
                    
            except Exception as e:
                st.error(f"Error generating chart: {str(e)}")
                st.info("Please select appropriate columns for the chart type.")
        
        st.markdown("---")
        
        # Parts Table
        st.markdown("#### Parts Details Table")
        
        # Create formatted display
        display_df = parts_df.copy()
        display_df['oem_price'] = display_df['oem_price'].apply(lambda x: f"₹{x:,.2f}")
        display_df['aftermarket_price'] = display_df['aftermarket_price'].apply(lambda x: f"₹{x:,.2f}" if pd.notnull(x) else "N/A")
        
        st.dataframe(
            display_df,
            column_config={
                "part_number": st.column_config.TextColumn(
                    "Part No.",
                    width="small"
                ),
                "part_name": st.column_config.TextColumn(
                    "Part Name",
                    width="medium"
                ),
                "oem_price": st.column_config.TextColumn(
                    "OEM Price"
                ),
                "aftermarket_price": st.column_config.TextColumn(
                    "Market Price"
                ),
                "stock_quantity": st.column_config.NumberColumn(
                    "In Stock",
                    help="Available units"
                ),
                "lead_time_days": st.column_config.NumberColumn(
                    "Lead Days",
                    help="Days to get if not in stock"
                )
            },
            use_container_width=True,
            height=400
        )
        
        # Price Comparison Chart
        st.markdown("#### Price Comparison Chart")
        
        top_parts = parts_df.head(8).copy()
        top_parts['savings'] = top_parts['oem_price'] - top_parts['aftermarket_price']
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=top_parts['part_name'],
            y=top_parts['oem_price'],
            name='OEM Price',
            marker_color='#1f77b4',
            hovertemplate='<b>%{x}</b><br>OEM: ₹%{y:,.2f}<extra></extra>'
        ))
        fig.add_trace(go.Bar(
            x=top_parts['part_name'],
            y=top_parts['aftermarket_price'],
            name='Aftermarket Price',
            marker_color='#ff7f0e',
            hovertemplate='<b>%{x}</b><br>Market: ₹%{y:,.2f}<extra></extra>'
        ))
        
        fig.update_layout(
            title="OEM vs Aftermarket Price Comparison",
            xaxis_title="Part Name",
            yaxis_title="Price (₹)",
            barmode='group',
            height=500,
            hovermode='x unified',
            xaxis_tickangle=45
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Savings analysis
        st.markdown("##### 💰 Potential Savings with Aftermarket Parts")
        savings_df = parts_df.copy()
        savings_df['savings_percent'] = ((savings_df['oem_price'] - savings_df['aftermarket_price']) / savings_df['oem_price'] * 100).round(1)
        savings_df['savings_amount'] = (savings_df['oem_price'] - savings_df['aftermarket_price']).round(2)
        
        top_savings = savings_df.nlargest(5, 'savings_amount')
        
        for _, part in top_savings.iterrows():
            col_s1, col_s2 = st.columns([3, 1])
            with col_s1:
                st.write(f"**{part['part_name']}**: Save ₹{part['savings_amount']:.2f} ({part['savings_percent']}%)")
            with col_s2:
                if st.button("View Details", key=f"view_{part['part_number']}"):
                    st.session_state['selected_part'] = part['part_number']
        
        # Download option
        csv = parts_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Parts Catalog (CSV)",
            data=csv,
            file_name=f"parts_catalog_{make_filter if make_filter != 'All' else 'all'}.csv",
            mime="text/csv"
        )
        
        # Search specific part
        st.markdown("---")
        st.markdown("#### 🔍 Search Specific Part")
        search_term = st.text_input("Enter part name or number")
        
        if search_term:
            search_results = parts_df[
                parts_df['part_name'].str.contains(search_term, case=False) | 
                parts_df['part_number'].str.contains(search_term, case=False)
            ]
            
            if not search_results.empty:
                st.success(f"Found {len(search_results)} matching parts")
                for _, part in search_results.iterrows():
                    st.markdown(f"""
                    <div class="part-card">
                        <h4>{part['part_name']} ({part['part_number']})</h4>
                        <p><strong>Make:</strong> {part['make']} | <strong>Model:</strong> {part['model']}</p>
                        <p><strong>OEM Price:</strong> ₹{part['oem_price']:,.2f} | 
                           <strong>Market Price:</strong> ₹{part['aftermarket_price']:,.2f}</p>
                        <p><strong>Stock:</strong> {part['stock_quantity']} units | 
                           <strong>Lead Time:</strong> {part['lead_time_days']} days</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No parts found matching your search")
    else:
        st.info("No parts found matching your criteria.")
# Add to app.py - After other render functions, before main()

def render_garage_dashboard():
    st.markdown("# 🛠️ Garage Dashboard")
    
    # Helper function to get garages
    def get_all_garages_safe():
        from database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM garages ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_breakdowns_for_garage_safe(garage_id):
        from database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.*, v.make, v.model, v.year, v.owner_name, v.owner_phone, v.vin
                FROM breakdown_incidents b
                JOIN vehicles v ON b.vehicle_id = v.id
                WHERE b.garage_id = ? 
                ORDER BY b.reported_at DESC
            ''', (garage_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def update_breakdown_status_safe(incident_id, status):
        from database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE breakdown_incidents 
                SET status = ?
                WHERE id = ?
            ''', (status, incident_id))
            conn.commit()
    
    # Get all garages
    garages = get_all_garages_safe()
    
    if not garages:
        st.warning("No garages found in database.")
        return
    
    # Garage selection in sidebar
    with st.sidebar.expander("🔐 Garage Login", expanded=True):
        garage_options = {g['name']: g['id'] for g in garages}
        selected_garage_name = st.selectbox("Select Your Garage", list(garage_options.keys()))
        
        if st.button("Login as Garage"):
            st.session_state['garage_id'] = garage_options[selected_garage_name]
            st.session_state['garage_name'] = selected_garage_name
            st.success(f"Logged in as {selected_garage_name}")
            st.rerun()
    
    # If not logged in, show selection
    if 'garage_id' not in st.session_state:
        st.info("👈 Please select your garage from the sidebar and click 'Login as Garage'")
        
        # Show all garages
        st.markdown("### Available Garages")
        cols = st.columns(2)
        for idx, garage in enumerate(garages):
            with cols[idx % 2]:
                st.markdown(f"""
                <div style='border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin: 10px 0;'>
                    <h4>🏢 {garage['name']}</h4>
                    <p><strong>📍</strong> {garage['address']}</p>
                    <p><strong>📞</strong> {garage['phone']}</p>
                    <p><strong>⭐</strong> {garage['rating']}/5</p>
                    <p><strong>⏱️</strong> {garage['estimated_response_time']} min response</p>
                    <p><strong>📊</strong> {garage['current_load']}/{garage['capacity']} jobs</p>
                </div>
                """, unsafe_allow_html=True)
        return
    
    # Garage is logged in - show dashboard
    garage_id = st.session_state['garage_id']
    garage_name = st.session_state['garage_name']
    
    def get_garage_by_id_safe(garage_id):
        from database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM garages WHERE id = ?", (garage_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    garage = get_garage_by_id_safe(garage_id)
    if not garage:
        st.error("Garage not found!")
        del st.session_state['garage_id']
        st.rerun()
    
    # Get breakdowns for this garage
    breakdowns = get_breakdowns_for_garage_safe(garage_id)
    active_jobs = [b for b in breakdowns if b['status'] in ['assigned', 'in_progress']]
    completed_jobs = [b for b in breakdowns if b['status'] == 'completed']
    
    # Header
    st.markdown(f"## 🏢 {garage_name}")
    
    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Active Jobs", len(active_jobs))
    with col2:
        st.metric("Total Jobs", len(breakdowns))
    with col3:
        st.metric("Capacity", f"{garage['current_load']}/{garage['capacity']}")
    with col4:
        utilization = (garage['current_load'] / garage['capacity']) * 100 if garage['capacity'] > 0 else 0
        st.metric("Utilization", f"{utilization:.1f}%")
    
    # Logout button
    if st.button("🚪 Logout", key="logout_garage"):
        del st.session_state['garage_id']
        st.success("Logged out")
        st.rerun()
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2 = st.tabs(["📋 Active Jobs", "🏢 Garage Info"])
    
    with tab1:
        st.markdown(f"### Breakdown Jobs ({len(breakdowns)})")
        
        if not breakdowns:
            st.info("No jobs assigned to your garage.")
        else:
            for job in breakdowns:
                status_color = {
                    'reported': 'gray',
                    'assigned': 'orange',
                    'in_progress': 'blue',
                    'completed': 'green'
                }.get(job['status'], 'gray')
                
                with st.expander(f"#{job['id']} - {job['breakdown_type']} - {job['make']} {job['model']}", expanded=False):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.write(f"**Vehicle:** {job['make']} {job['model']} ({job['year']})")
                        st.write(f"**Owner:** {job['owner_name']}")
                        st.write(f"**Phone:** {job['owner_phone']}")
                        st.write(f"**VIN:** {job['vin']}")
                    
                    with col_b:
                        st.write(f"**Status:** :{status_color}[{job['status'].replace('_', ' ').title()}]")
                        st.write(f"**Reported:** {job['reported_at'][:16]}")
                        st.write(f"**Est. Fix:** {job.get('estimated_fix_time', 'N/A')} mins")
                    
                    # Action buttons
                    if job['status'] == 'assigned':
                        col_x, col_y = st.columns(2)
                        with col_x:
                            if st.button("🛠️ Start Repair", key=f"start_{job['id']}"):
                                update_breakdown_status_safe(job['id'], 'in_progress')
                                st.success("Job status updated to 'In Progress'")
                                st.rerun()
                        with col_y:
                            if st.button("📞 Call Customer", key=f"call_{job['id']}"):
                                st.info(f"📱 Calling {job['owner_name']} at {job['owner_phone']}")
                    
                    elif job['status'] == 'in_progress':
                        notes = st.text_area("Repair notes", key=f"notes_{job['id']}", placeholder="Describe what was fixed...")
                        
                        col_x, col_y = st.columns(2)
                        with col_x:
                            parts_cost = st.number_input("Parts Cost (₹)", min_value=0, value=500, key=f"parts_{job['id']}")
                        with col_y:
                            labor_cost = st.number_input("Labor Cost (₹)", min_value=0, value=1000, key=f"labor_{job['id']}")
                        
                        if st.button("✅ Mark as Completed", key=f"complete_{job['id']}", type="primary"):
                            total_cost = parts_cost + labor_cost
                            
                            # Update the breakdown record
                            from database import get_db_connection
                            import json
                            with get_db_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute('''
                                    UPDATE breakdown_incidents 
                                    SET status = 'completed', 
                                        total_cost = ?
                                    WHERE id = ?
                                ''', (total_cost, job['id']))
                                conn.commit()
                            
                            st.success(f"Job completed! Total: ₹{total_cost}")
                            st.balloons()
                            st.rerun()
    
    with tab2:
        st.markdown("### Garage Information")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"""
            #### {garage['name']}
            
            **📍 Address:** {garage['address']}
            
            **📞 Phone:** {garage['phone']}
            
            **⭐ Rating:** {garage['rating']}/5
            
            **🔧 Specialization:** {garage['specialization']}
            
            **⏱️ Response Time:** {garage['estimated_response_time']} minutes
            
            **🕒 Operating Hours:** {garage['operating_hours']}
            
            **📊 Capacity:** {garage['current_load']}/{garage['capacity']} vehicles
            """)
        
        with col2:
            # Update capacity
            st.markdown("#### Update Capacity")
            new_capacity = st.number_input("New Capacity", min_value=1, max_value=50, value=garage['capacity'])
            if st.button("Update Capacity"):
                from database import get_db_connection
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE garages 
                        SET capacity = ?
                        WHERE id = ?
                    ''', (new_capacity, garage_id))
                    conn.commit()
                st.success("Garage capacity updated!")
                st.rerun()

def render_active_jobs_tab(garage_id, garage_name):
    st.markdown(f"### 🚧 Active Breakdowns - {garage_name}")
    
    # Get active breakdowns
    breakdowns = get_breakdowns_by_garage_and_status(garage_id, ['assigned', 'in_progress'])
    
    if not breakdowns:
        st.info("No active breakdowns assigned to your garage.")
        return
    
    for breakdown in breakdowns:
        status_color = {
            'assigned': 'warning',
            'in_progress': 'info',
            'completed': 'success'
        }.get(breakdown['status'], 'secondary')
        
        with st.expander(f"#{breakdown['id']} - {breakdown['breakdown_type']} - {breakdown['make']} {breakdown['model']}", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Vehicle:** {breakdown['make']} {breakdown['model']} ({breakdown['year']})")
                st.write(f"**Owner:** {breakdown['owner_name']}")
                st.write(f"**Phone:** {breakdown['owner_phone']}")
                st.write(f"**VIN:** {breakdown['vin']}")
                st.write(f"**Location:** {breakdown['breakdown_location_lat']:.4f}, {breakdown['breakdown_location_lng']:.4f}")
            
            with col2:
                st.write(f"**Reported:** {breakdown['reported_at'][:16]}")
                st.write(f"**Est. Fix Time:** {breakdown.get('estimated_fix_time', 'Not set')} mins")
                st.write(f"**Status:** :{status_color}[{breakdown['status'].replace('_', ' ').title()}]")
                
                if breakdown.get('technician_id'):
                    tech = get_technician_by_id(breakdown['technician_id'])
                    if tech:
                        st.write(f"**Technician:** {tech['name']}")
            
            # Action buttons based on status
            if breakdown['status'] == 'assigned':
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("🚗 Dispatch Technician", key=f"dispatch_{breakdown['id']}"):
                        start_breakdown_fix(breakdown['id'])
                        st.success("Job status updated to 'In Progress'")
                        st.rerun()
                with col_b:
                    if st.button("📞 Call Customer", key=f"call_{breakdown['id']}"):
                        st.info(f"Calling {breakdown['owner_name']} at {breakdown['owner_phone']}")
                with col_c:
                    if st.button("🗺️ Get Directions", key=f"dir_{breakdown['id']}"):
                        maps_url = f"https://www.google.com/maps/dir/?api=1&destination={breakdown['breakdown_location_lat']},{breakdown['breakdown_location_lng']}"
                        st.markdown(f"[Open in Google Maps]({maps_url})", unsafe_allow_html=True)
            
            elif breakdown['status'] == 'in_progress':
                st.markdown("#### 🛠️ Fix in Progress")
                
                # Progress tracking
                progress = st.slider("Progress (%)", 0, 100, 50, key=f"progress_{breakdown['id']}")
                
                # Parts used
                st.subheader("📦 Parts Used")
                available_parts = get_parts_catalog(make=breakdown['make'])
                
                selected_parts = st.multiselect(
                    "Select parts used",
                    [f"{p['part_number']} - {p['part_name']} (₹{p['aftermarket_price']})" for p in available_parts],
                    key=f"parts_{breakdown['id']}"
                )
                
                # Labor cost
                labor_hours = st.number_input("Labor Hours", min_value=0.5, max_value=10.0, value=2.0, step=0.5, key=f"labor_{breakdown['id']}")
                hourly_rate = st.number_input("Hourly Rate (₹)", min_value=500, max_value=2000, value=800, key=f"rate_{breakdown['id']}")
                
                # Notes
                technician_notes = st.text_area("Technician Notes", placeholder="Describe the issue and fix applied...", key=f"notes_{breakdown['id']}")
                
                col_x, col_y = st.columns(2)
                with col_x:
                    if st.button("⏸️ Pause Job", key=f"pause_{breakdown['id']}"):
                        update_breakdown_status(breakdown['id'], 'on_hold', technician_notes)
                        st.warning("Job paused")
                        st.rerun()
                with col_y:
                    if st.button("✅ Complete Job", type="primary", key=f"complete_{breakdown['id']}"):
                        # Calculate total cost
                        parts_cost = sum(float(p.split('₹')[1].split(')')[0]) for p in selected_parts)
                        labor_cost = labor_hours * hourly_rate
                        total_cost = parts_cost + labor_cost
                        
                        # Actual fix time (in minutes)
                        actual_time = st.number_input("Actual Fix Time (minutes)", min_value=15, max_value=480, value=breakdown.get('estimated_fix_time', 60), key=f"time_{breakdown['id']}")
                        
                        # Record completion
                        parts_used = []
                        for part_str in selected_parts:
                            part_num = part_str.split(' - ')[0]
                            parts_used.append({
                                'part_number': part_num,
                                'quantity': 1,
                                'price': float(part_str.split('₹')[1].split(')')[0])
                            })
                        
                        complete_breakdown_fix(
                            incident_id=breakdown['id'],
                            parts_used=parts_used,
                            total_cost=total_cost,
                            actual_fix_time=actual_time,
                            notes=technician_notes
                        )
                        
                        # Update inventory
                        use_parts_for_breakdown(breakdown['id'], parts_used)
                        
                        # Generate invoice
                        invoice = generate_breakdown_invoice(breakdown['id'])
                        
                        st.success(f"Job completed! Total cost: ₹{total_cost:.2f}")
                        st.balloons()
                        
                        # Show invoice
                        with st.expander("📄 View Invoice"):
                            st.json(invoice)
                        
                        st.rerun()

def render_parts_inventory_tab(garage_id):
    st.markdown("### 📦 Parts Inventory Management")
    
    # Get all parts
    parts = get_parts_catalog()
    
    # Filter and search
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("Search parts")
    with col2:
        category_filter = st.selectbox("Filter by category", ["All", "Engine", "Electrical", "Brakes", "Tires", "Suspension", "Cooling"])
    
    # Filter parts
    filtered_parts = parts
    if search_term:
        filtered_parts = [p for p in parts if search_term.lower() in p['part_name'].lower() or search_term in p['part_number']]
    if category_filter != "All":
        filtered_parts = [p for p in filtered_parts if p['category'] == category_filter]
    
    # Low stock warning
    low_stock = [p for p in filtered_parts if p['stock_quantity'] < 5]
    if low_stock:
        st.warning(f"⚠️ {len(low_stock)} parts are low on stock!")
        for part in low_stock[:3]:
            st.write(f"• {part['part_name']} - Only {part['stock_quantity']} left")
    
    # Display parts in a nice grid
    for part in filtered_parts[:20]:  # Limit to first 20
        with st.expander(f"{part['part_name']} ({part['part_number']}) - Stock: {part['stock_quantity']}"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Category:** {part['category']}")
                st.write(f"**Make:** {part['make']}")
                st.write(f"**Model:** {part['model']}")
                st.write(f"**Years:** {part['year_from']}-{part['year_to']}")
            with col_b:
                st.write(f"**OEM Price:** ₹{part['oem_price']:.2f}")
                st.write(f"**Market Price:** ₹{part['aftermarket_price']:.2f}")
                st.write(f"**Lead Time:** {part['lead_time_days']} days")
            
            # Stock management
            col_x, col_y, col_z = st.columns([2, 1, 1])
            with col_x:
                new_stock = st.number_input("Update stock quantity", min_value=0, value=part['stock_quantity'], key=f"stock_{part['id']}")
            with col_y:
                if st.button("Update", key=f"update_{part['id']}"):
                    quantity_change = new_stock - part['stock_quantity']
                    if update_part_stock(part['id'], quantity_change):
                        st.success("Stock updated!")
                        st.rerun()
            with col_z:
                if st.button("Reorder", key=f"reorder_{part['id']}"):
                    st.info(f"Reorder request sent for {part['part_name']}")

def render_technicians_tab(garage_id):
    st.markdown("### 👨‍🔧 Technician Management")
    
    # Get technicians
    technicians = get_garage_technicians(garage_id)
    
    # Add new technician
    with st.form("add_technician_form"):
        st.markdown("#### Add New Technician")
        col1, col2 = st.columns(2)
        with col1:
            tech_name = st.text_input("Name")
            specialization = st.selectbox("Specialization", ["General", "Engine", "Electrical", "Brakes", "Transmission", "AC"])
        with col2:
            contact = st.text_input("Contact Number")
            experience = st.number_input("Experience (years)", min_value=0, max_value=50, value=3)
        
        if st.form_submit_button("➕ Add Technician"):
            if tech_name and contact:
                create_technician(garage_id, tech_name, specialization, contact, experience)
                st.success(f"Technician {tech_name} added!")
                st.rerun()
    
    # Display technicians
    st.markdown("#### Current Technicians")
    if technicians:
        cols = st.columns(3)
        for idx, tech in enumerate(technicians):
            with cols[idx % 3]:
                status_color = "green" if tech['status'] == 'available' else "red" if tech['status'] == 'busy' else "gray"
                st.markdown(f"""
                <div style='border: 1px solid #ddd; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                    <h4>👨‍🔧 {tech['name']}</h4>
                    <p><strong>Status:</strong> <span style='color:{status_color}'>{tech['status'].title()}</span></p>
                    <p><strong>Specialization:</strong> {tech['specialization']}</p>
                    <p><strong>Contact:</strong> {tech['contact']}</p>
                    <p><strong>Exp:</strong> {tech.get('experience_years', 0)} years</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Assign to breakdown if available
                if tech['status'] == 'available':
                    active_jobs = get_breakdowns_by_garage_and_status(garage_id, ['assigned'])
                    if active_jobs:
                        job_options = {f"#{j['id']} - {j['make']} {j['model']}": j['id'] for j in active_jobs}
                        selected_job = st.selectbox(f"Assign job to {tech['name']}", ["Select job"] + list(job_options.keys()), key=f"assign_{tech['id']}")
                        if selected_job != "Select job" and st.button("Assign", key=f"assignbtn_{tech['id']}"):
                            assign_technician(job_options[selected_job], tech['id'])
                            st.success(f"Assigned {tech['name']} to {selected_job}")
                            st.rerun()
    else:
        st.info("No technicians added yet. Add your first technician above.")

def render_garage_analytics_tab(garage_id):
    st.markdown("### 📊 Garage Analytics")
    
    # Get analytics data
    analytics = get_garage_analytics(garage_id)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Monthly Performance")
        # Create a simple bar chart for monthly completions
        monthly_data = analytics.get('monthly_completions', {})
        if monthly_data:
            months = list(monthly_data.keys())
            completions = list(monthly_data.values())
            
            fig = go.Figure(data=[
                go.Bar(x=months, y=completions, marker_color='#36A2EB')
            ])
            fig.update_layout(
                title="Jobs Completed Per Month",
                xaxis_title="Month",
                yaxis_title="Number of Jobs",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Revenue Trend")
        revenue_data = analytics.get('monthly_revenue', {})
        if revenue_data:
            months = list(revenue_data.keys())
            revenue = list(revenue_data.values())
            
            fig = go.Figure(data=[
                go.Scatter(x=months, y=revenue, mode='lines+markers', line=dict(color='#4BC0C0', width=3))
            ])
            fig.update_layout(
                title="Monthly Revenue (₹)",
                xaxis_title="Month",
                yaxis_title="Revenue",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Customer ratings
    st.markdown("#### Customer Feedback")
    feedback = get_garage_feedback(garage_id)
    
    if feedback:
        avg_rating = sum(f['rating'] for f in feedback) / len(feedback)
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Average Rating", f"{avg_rating:.1f}/5")
        with col_b:
            positive = sum(1 for f in feedback if f['rating'] >= 4)
            st.metric("Positive Reviews", positive)
        with col_c:
            response_rate = analytics.get('response_rate', 0)
            st.metric("Avg Response Time", f"{analytics.get('avg_response_time', 0):.0f} mins")
        
        # Show recent feedback
        st.markdown("##### Recent Comments")
        for fb in feedback[:3]:
            stars = "⭐" * fb['rating'] + "☆" * (5 - fb['rating'])
            st.markdown(f"""
            <div style='background: #f8f9fa; padding: 10px; border-radius: 5px; margin: 5px 0;'>
                <p><strong>{stars}</strong></p>
                <p><em>"{fb.get('comments', 'No comment')}"</em></p>
                <p style='font-size: 0.8em; color: #666;'>{fb.get('vehicle_model', 'Unknown')} • {fb.get('created_at', '')[:10]}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No customer feedback yet.")

# Add to the navigation in main() function
# In the radio selector, add "Garage Dashboard":

def render_architecture():
    st.markdown("## System Architecture")
    
    st.markdown("""
    ### AutoSenseAI - Agentic AI Platform for Predictive Maintenance
    
    AutoSenseAI is a comprehensive predictive maintenance platform designed for the automotive industry,
    specifically tailored for Hero and Mahindra vehicles. The system uses a multi-agent AI architecture
    to autonomously predict failures, diagnose issues, schedule services, and maintain a continuous
    feedback loop with OEM manufacturing teams.
    """)
    
    st.markdown("### Architecture Diagram")
    
    st.markdown("""
    ```
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                           AUTOSENSEAI PLATFORM                               │
    ├─────────────────────────────────────────────────────────────────────────────┤
    │                                                                              │
    │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
    │   │   VEHICLE   │    │   SERVICE   │    │     OEM     │                     │
    │   │   OWNER     │    │   CENTER    │    │  DASHBOARD  │                     │
    │   │   PORTAL    │    │    VIEW     │    │             │                     │
    │   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                     │
    │          │                  │                  │                            │
    │          └──────────────────┼──────────────────┘                            │
    │                             │                                               │
    │                    ┌────────┴────────┐                                      │
    │                    │  STREAMLIT UI   │                                      │
    │                    └────────┬────────┘                                      │
    │                             │                                               │
    ├─────────────────────────────┼───────────────────────────────────────────────┤
    │                             │                                               │
    │              ┌──────────────┴──────────────┐                                │
    │              │       MASTER AGENT          │                                │
    │              │    (Orchestration Layer)    │                                │
    │              └──────────────┬──────────────┘                                │
    │                             │                                               │
    │     ┌───────────┬───────────┼───────────┬───────────┐                       │
    │     │           │           │           │           │                       │
    │ ┌───┴───┐  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐ ┌────┴────┐                  │
    │ │PREDICT│  │DIAGNOSE │ │SCHEDULE │ │CUSTOMER │ │   RCA   │                  │
    │ │ AGENT │  │  AGENT  │ │  AGENT  │ │  AGENT  │ │  AGENT  │                  │
    │ └───┬───┘  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                  │
    │     │           │           │           │           │                       │
    ├─────┼───────────┼───────────┼───────────┼───────────┼───────────────────────┤
    │     │           │           │           │           │                       │
    │ ┌───┴───────────┴───────────┴───────────┴───────────┴───┐                   │
    │ │                    ML ENGINE                          │                   │
    │ │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │                   │
    │ │  │  Isolation  │  │   Random    │  │  Component  │   │                   │
    │ │  │   Forest    │  │   Forest    │  │   Health    │   │                   │
    │ │  │  (Anomaly)  │  │ (Failure)   │  │  Analysis   │   │                   │
    │ │  └─────────────┘  └─────────────┘  └─────────────┘   │                   │
    │ └───────────────────────────┬───────────────────────────┘                   │
    │                             │                                               │
    ├─────────────────────────────┼───────────────────────────────────────────────┤
    │                             │                                               │
    │ ┌───────────────────────────┴───────────────────────────┐                   │
    │ │                     DATA LAYER                        │                   │
    │ │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │                   │
    │ │  │Vehicles │  │ Alerts  │  │Bookings │  │Feedback │  │                   │
    │ │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │                   │
    │ │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │                   │
    │ │  │Telemetry│  │ Service │  │  Agent  │  │   RCA   │  │                   │
    │ │  │  Data   │  │ Centers │  │  Logs   │  │ Reports │  │                   │
    │ │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │                   │
    │ └───────────────────────────────────────────────────────┘                   │
    │                                                                              │
    └─────────────────────────────────────────────────────────────────────────────┘
    ```
    """)
    
    st.markdown("### Agent Responsibilities")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **Master Agent (Orchestrator)**
        - Coordinates all worker agents
        - Manages workflow execution
        - Aggregates results and decisions
        - Logs all agent activities
        
        **Prediction Agent**
        - Analyzes telemetry data
        - Runs ML models (Isolation Forest, Random Forest)
        - Calculates failure probabilities
        - Generates health scores
        
        **Diagnosis Agent**
        - Identifies root causes
        - Maps symptoms to possible issues
        - Recommends repair actions
        - Estimates repair time and parts
        """)
    
    with col2:
        st.markdown("""
        **Scheduling Agent**
        - Selects optimal service center
        - Finds available time slots
        - Prioritizes based on urgency
        - Creates booking records
        
        **Customer Agent**
        - Sends alerts and notifications
        - Handles chat interactions
        - Confirms bookings
        - Collects feedback
        
        **RCA Feedback Agent**
        - Analyzes failure patterns
        - Generates root cause reports
        - Aggregates service feedback
        - Notifies OEM for manufacturing insights
        """)
    
    st.markdown("### Data Flow")
    
    st.markdown("""
    ```
    Vehicle Telemetry → Prediction Agent → Anomaly Detection → Failure Prediction
                                              ↓
                                        Diagnosis Agent → Root Cause Analysis
                                              ↓
                                        Scheduling Agent → Service Booking
                                              ↓
                                        Customer Agent → Notification
                                              ↓
                                        Service Completion → Feedback Collection
                                              ↓
                                        RCA Agent → OEM Manufacturing Insights
    ```
    """)

def main():
    st.sidebar.markdown("# 🚗 AutoSenseAI")
    st.sidebar.markdown("*Predictive Maintenance Platform*")
    st.sidebar.markdown("---")
    
    view = st.sidebar.radio(
    "Select View",
    ["OEM Dashboard", "Service Center", "Vehicle Owner", "Breakdown Assistance", 
     "Parts Catalog", "Telemetry Simulator", "Agent Logs", "Architecture", 
     "Garage Dashboard"],  # ← Add this
    index=0
)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Stats")
    stats = get_dashboard_stats()
    st.sidebar.metric("Fleet Health", f"{100 - (stats['critical_vehicles'] / max(stats['total_vehicles'], 1)) * 100:.0f}%")
    st.sidebar.metric("Active Alerts", stats['active_alerts'])
    
    # Add emergency contacts to sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🚨 Emergency Contacts")
    st.sidebar.info("""
    **Roadside Assistance:** 1800-123-4567  
    **Police:** 100  
    **Ambulance:** 102  
    **Fire:** 101  
    **National Helpline:** 112
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info("""
    AutoSenseAI is an Agentic AI platform for predictive vehicle maintenance.
    
    **New Features:**
    - 🚨 Breakdown Assistance with nearby garages
    - 🔧 Parts Catalog with OEM pricing
    - 📊 Tabular to Chart visualization
    - ⏱️ Estimated fix times
    
    *Built for EY Techathon 6.0*
    """)
    
    if view == "OEM Dashboard":
        render_oem_dashboard()
    elif view == "Service Center":
        render_service_center_view()
    elif view == "Vehicle Owner":
        render_vehicle_owner_portal()
    elif view == "Breakdown Assistance":
        render_breakdown_assistance()
    elif view == "Parts Catalog":
        render_parts_catalog()
    elif view == "Telemetry Simulator":
        render_telemetry_simulator()
    elif view == "Agent Logs":
        render_agent_logs()
    elif view == "Architecture":
        render_architecture()
    elif view == "Garage Dashboard":
        render_garage_dashboard()

if __name__ == "__main__":
    main()
