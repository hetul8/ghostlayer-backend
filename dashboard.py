import streamlit as st
import pandas as pd
import requests
import time
from faker import Faker

# Config
st.set_page_config(
    page_title="GhostLayer Cloud Admin",
    page_icon="👻",
    layout="wide",
)

st.title("👻 GhostLayer Cloud Admin Panel")

# Init Faker
fake = Faker()

# Configuration
API_URL = "https://ghostlayer-backend.onrender.com" # Production URL
API_KEY = "ghost_123_secret" # In a real app, use st.secrets

def get_stats():
    try:
        response = requests.get(
            f"{API_URL}/stats",
            headers={"X-API-Key": API_KEY},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            st.error("Unauthorized! Check your API Key.")
        else:
            st.error(f"API Error: {response.status_code}")
    except Exception as e:
        st.error(f"Connection Error: {e}")
    return None

def simulate_traffic():
    with st.spinner("Injecting traffic..."):
        for _ in range(3):
            if fake.boolean():
                text = f"Email: {fake.email()}"
            else:
                text = f"Phone: {fake.phone_number()}"
            
            try:
                requests.post(
                    f"{API_URL}/mask",
                    json={"text": text},
                    headers={"X-API-Key": API_KEY}
                )
            except:
                pass
    st.success("Traffic sent to cloud!")

# Sidebar
st.sidebar.header("Controls")
if st.sidebar.button("Refresh Data"):
    st.rerun()

if st.sidebar.button("Simulate Cloud Traffic"):
    simulate_traffic()
    time.sleep(1)
    st.rerun()

# Main Logic
stats = get_stats()

if stats:
    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Secrets", stats.get("total", 0))
    col2.metric("Emails Blocked", stats.get("emails", 0))
    col3.metric("Phone Numbers", stats.get("phones", 0))
    
    # Recent Logs
    st.subheader("Recent Activity Log")
    logs = stats.get("recent_logs", [])
    if logs:
        df = pd.DataFrame(logs)
        # Reorder columns
        df = df[["timestamp", "type", "masked_id", "id"]]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No activity recorded yet.")
else:
    st.warning("Waiting for data connection...")
