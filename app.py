import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time

from database import (
    init_database, seed_sample_data, get_all_vehicles, get_vehicle_by_id,
    get_all_alerts, get_all_service_centers, get_all_bookings, get_all_feedback,
    get_dashboard_stats, get_agent_logs, get_rca_reports, update_booking_status,
    create_feedback, get_telemetry_history, save_telemetry
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
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_app():
    init_database()
    seed_sample_data()
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
            from database import create_booking
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
        ["OEM Dashboard", "Service Center", "Vehicle Owner", "Telemetry Simulator", "Agent Logs", "Architecture"],
        index=0
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Stats")
    stats = get_dashboard_stats()
    st.sidebar.metric("Fleet Health", f"{100 - (stats['critical_vehicles'] / max(stats['total_vehicles'], 1)) * 100:.0f}%")
    st.sidebar.metric("Active Alerts", stats['active_alerts'])
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info("""
    AutoSenseAI is an Agentic AI platform for predictive vehicle maintenance.
    
    **Features:**
    - Multi-agent AI orchestration
    - ML-based failure prediction
    - Smart service scheduling
    - OEM feedback loop
    
    *Built for EY Techathon 6.0*
    """)
    
    if view == "OEM Dashboard":
        render_oem_dashboard()
    elif view == "Service Center":
        render_service_center_view()
    elif view == "Vehicle Owner":
        render_vehicle_owner_portal()
    elif view == "Telemetry Simulator":
        render_telemetry_simulator()
    elif view == "Agent Logs":
        render_agent_logs()
    elif view == "Architecture":
        render_architecture()

if __name__ == "__main__":
    main()
