import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json

# Configuration
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Forecasting Prototype",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Forecasting Prototype")
st.markdown("*A thin wrapper around StatsForecast for business-focused forecasting*")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.selectbox("Choose a page", [
    "🔄 Upload Data", 
    "🧪 Run Backtest", 
    "📊 Generate Forecast", 
    "🚨 Configure Alerts"
])

def upload_dataset():
    st.header("🔄 Upload Dataset")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose a CSV file", 
        type="csv",
        help="Expected columns: timestamp, series_id, y, capacity (optional)"
    )
    
    if uploaded_file is not None:
        # Preview data
        df = pd.read_csv(uploaded_file)
        st.subheader("Data Preview")
        st.dataframe(df.head(10))
        
        # Dataset info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", len(df))
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            if 'series_id' in df.columns:
                st.metric("Unique Series", df['series_id'].nunique())
        
        # Dataset name
        dataset_name = st.text_input(
            "Dataset Name", 
            value=uploaded_file.name.replace('.csv', '')
        )
        
        # Upload button
        if st.button("Upload Dataset", type="primary"):
            with st.spinner("Uploading and validating dataset..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                    data = {"name": dataset_name}
                    
                    response = requests.post(
                        f"{API_BASE_URL}/datasets/upload",
                        files=files,
                        data=data
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Dataset '{dataset_name}' uploaded successfully!")
                        
                        # Show validation results
                        st.subheader("Validation Results")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Series Count", result['n_series'])
                            st.metric("Total Observations", result['n_observations'])
                        with col2:
                            st.json(result['schema'])
                        
                        # Store dataset ID in session state
                        st.session_state.dataset_id = result['id']
                        st.session_state.dataset_name = result['name']
                        
                    else:
                        st.error(f"❌ Upload failed: {response.json().get('detail', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

def run_backtest():
    st.header("🧪 Run Backtest")
    
    # Check if we have a dataset
    if 'dataset_id' not in st.session_state:
        st.warning("⚠️ Please upload a dataset first!")
        return
    
    st.info(f"Using dataset: **{st.session_state.dataset_name}**")
    
    # Backtest configuration
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Model Configuration")
        models = st.multiselect(
            "Select Models",
            ["AutoARIMA", "ETS", "Theta"],
            default=["AutoARIMA", "ETS", "Theta"]
        )
        
        horizon = st.slider("Forecast Horizon (days)", 7, 30, 14)
        
    with col2:
        st.subheader("Validation Settings")
        n_folds = st.slider("Number of Folds", 2, 5, 3)
        quantiles = st.multiselect(
            "Quantiles",
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            default=[0.1, 0.5, 0.9]
        )
    
    # Run backtest
    if st.button("Run Backtest", type="primary"):
        if not models:
            st.error("Please select at least one model!")
            return
            
        with st.spinner("Running backtest... This may take a few minutes."):
            try:
                payload = {
                    "dataset_id": st.session_state.dataset_id,
                    "models": models,
                    "horizon": horizon,
                    "quantiles": quantiles,
                    "n_folds": n_folds
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/models/backtest",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Backtest completed!")
                    
                    # Store results
                    st.session_state.model_config_id = result['model_config_id']
                    st.session_state.backtest_result = result
                    
                    # Display results
                    st.subheader("📊 Backtest Results")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Winner Model", result['winner_model'])
                    with col2:
                        st.metric("WAPE", f"{result['wape']:.3f}")
                    with col3:
                        st.metric("Capacity Breach Rate", f"{result['capacity_breach_rate']:.3f}")
                    
                    # Model comparison
                    st.subheader("Model Comparison")
                    results_df = pd.DataFrame(result['model_results'])
                    st.dataframe(results_df)
                    
                    # Plot comparison
                    if len(results_df) > 1:
                        fig = px.bar(
                            results_df, 
                            x='model', 
                            y='wape',
                            title="Model Performance (WAPE - Lower is Better)"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.error(f"❌ Backtest failed: {response.json().get('detail', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

def generate_forecast():
    st.header("📊 Generate Forecast")
    
    # Check if we have a trained model
    if 'model_config_id' not in st.session_state:
        st.warning("⚠️ Please run a backtest first!")
        return
    
    st.info(f"Using model: **{st.session_state.backtest_result['winner_model']}** (WAPE: {st.session_state.backtest_result['wape']:.3f})")
    
    if st.button("Generate Forecasts", type="primary"):
        with st.spinner("Generating forecasts..."):
            try:
                payload = {
                    "model_config_id": st.session_state.model_config_id
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/forecasts/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Forecasts generated!")
                    
                    # Store forecast ID
                    st.session_state.forecast_id = result['forecast_id']
                    
                    # Display forecast info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Forecast ID", result['forecast_id'])
                    with col2:
                        st.metric("Series Count", result['n_series'])
                    with col3:
                        st.metric("Horizon", result['horizon'])
                    
                    # Show sample forecasts
                    if result['forecasts']:
                        st.subheader("Sample Forecasts")
                        forecasts_df = pd.DataFrame(result['forecasts'][:20])  # Show first 20
                        st.dataframe(forecasts_df)
                        
                        # Simple forecast plot for first series
                        if 'unique_id' in forecasts_df.columns:
                            first_series = forecasts_df['unique_id'].iloc[0]
                            series_data = forecasts_df[forecasts_df['unique_id'] == first_series]
                            
                            if len(series_data) > 0:
                                fig = go.Figure()
                                
                                # Add forecast line
                                if 'AutoARIMA' in series_data.columns:
                                    fig.add_trace(go.Scatter(
                                        x=series_data['ds'],
                                        y=series_data['AutoARIMA'],
                                        mode='lines+markers',
                                        name='Forecast',
                                        line=dict(color='blue')
                                    ))
                                
                                fig.update_layout(
                                    title=f"Forecast for Series: {first_series}",
                                    xaxis_title="Date",
                                    yaxis_title="Value"
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.error(f"❌ Forecast generation failed: {response.json().get('detail', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

def configure_alerts():
    st.header("🚨 Configure Alerts")
    
    # Check if we have a trained model
    if 'model_config_id' not in st.session_state:
        st.warning("⚠️ Please run a backtest first!")
        return
    
    st.info(f"Configuring alerts for model: **{st.session_state.backtest_result['winner_model']}**")
    
    # Alert configuration
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Alert Settings")
        alert_type = st.selectbox("Alert Type", ["capacity_breach"])
        threshold = st.slider(
            "Threshold (P90 demand level)", 
            0.1, 2.0, 0.9, 0.1,
            help="Alert when P90 forecast exceeds this threshold"
        )
    
    with col2:
        st.subheader("Notification")
        st.info("Alerts will be logged to console for this prototype")
    
    # Create alert
    if st.button("Create Alert", type="primary"):
        with st.spinner("Creating alert..."):
            try:
                payload = {
                    "model_config_id": st.session_state.model_config_id,
                    "alert_type": alert_type,
                    "threshold": threshold
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/alerts/create",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Alert created!")
                    
                    # Store alert ID
                    st.session_state.alert_id = result['id']
                    
                    # Display alert info
                    st.subheader("Alert Details")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Alert ID", result['id'])
                    with col2:
                        st.metric("Type", result['alert_type'])
                    with col3:
                        st.metric("Threshold", result['threshold'])
                
                else:
                    st.error(f"❌ Alert creation failed: {response.json().get('detail', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Test alert
    if 'alert_id' in st.session_state:
        st.subheader("Test Alert")
        if st.button("Check for Alerts", type="secondary"):
            with st.spinner("Checking for capacity alerts..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/alerts/check/{st.session_state.alert_id}"
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if result['alerts_triggered'] > 0:
                            st.warning(f"🚨 {result['alerts_triggered']} alerts triggered!")
                            
                            # Show alerts
                            for alert in result['alerts']:
                                st.error(f"**{alert['series_id']}** on {alert['date']}: {alert['message']}")
                        else:
                            st.success("✅ No alerts triggered")
                        
                        st.info("💡 Check the backend console for detailed alert logs")
                    
                    else:
                        st.error(f"❌ Alert check failed: {response.json().get('detail', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# Main app logic
if page == "🔄 Upload Data":
    upload_dataset()
elif page == "🧪 Run Backtest":
    run_backtest()
elif page == "📊 Generate Forecast":
    generate_forecast()
elif page == "🚨 Configure Alerts":
    configure_alerts()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Forecasting Prototype v1.0**")
st.sidebar.markdown("Built with StatsForecast + FastAPI + Streamlit")
