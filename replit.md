# AutoSenseAI - Predictive Maintenance Platform

## Overview
AutoSenseAI is an Agentic AI-based predictive maintenance platform designed for the automotive industry (Hero and Mahindra vehicles). Built for EY Techathon 6.0, it features autonomous failure prediction, smart service scheduling, and a closed-loop feedback system for OEM manufacturing teams.

## Project Structure
```
├── app.py                 # Main Streamlit application with all views
├── database.py            # SQLite database layer and data models
├── telemetry.py           # Vehicle telemetry simulator
├── predictive_engine.py   # ML-based prediction engine (Isolation Forest, Random Forest)
├── agents.py              # Multi-agent orchestration system
├── .streamlit/config.toml # Streamlit configuration
└── autosenseai.db         # SQLite database (auto-generated)
```

## Key Features
1. **Multi-Agent AI System**: Master agent coordinating 5 specialized worker agents
2. **Predictive Maintenance**: ML-based anomaly detection and failure prediction
3. **Smart Scheduling**: Automated service center selection and booking
4. **Customer Interaction**: Chat interface and notification system
5. **OEM Analytics**: Dashboard with RCA reports and manufacturing insights

## Tech Stack
- **Frontend**: Streamlit
- **Database**: SQLite
- **ML**: Scikit-learn (Isolation Forest, Random Forest)
- **Visualization**: Plotly
- **Data**: Pandas, NumPy

## Running the Application
```bash
streamlit run app.py --server.port 5000
```

## Views Available
1. **OEM Dashboard**: Fleet analytics, alerts, RCA reports
2. **Service Center**: Booking management, service tracking
3. **Vehicle Owner Portal**: Health status, bookings, AI chat
4. **Telemetry Simulator**: Generate test data and run analysis
5. **Agent Logs**: View multi-agent decision logs
6. **Architecture**: System documentation

## Agent Architecture
- **Master Agent**: Orchestrates workflow
- **Prediction Agent**: ML-based failure prediction
- **Diagnosis Agent**: Root cause analysis
- **Scheduling Agent**: Service center selection and booking
- **Customer Agent**: Notifications and chat
- **RCA Feedback Agent**: Manufacturing insights
