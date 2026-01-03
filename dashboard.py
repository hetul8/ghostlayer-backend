import streamlit as st
import pandas as pd
import requests
import time
from faker import Faker

# --- CONFIGURATION ---
API_URL = "https://ghostlayer-backend.onrender.com"
# API_KEY should ideally come from st.text_input for security, but hardcoded for MVP as requested.
API_KEY = "ghost_123_secret"

st.set_page_config(page_title="GhostLayer Cloud Admin", layout="wide", page_icon="👻")
st.title("👻 GhostLayer Cloud Admin Panel")

# --- SIDEBAR ---
st.sidebar.header("Connection")
if st.sidebar.button("Refresh Data"):
    st.rerun()

fake = Faker()
def simulate_traffic():
    with st.spinner("Injecting traffic to Cloud..."):
        for _ in range(3):
            text = f"Email: {fake.email()}" if fake.boolean() else f"Phone: {fake.phone_number()}"
            try:
                requests.post(f"{API_URL}/mask", json={"text": text}, headers={"X-API-Key": API_KEY})
            except: pass
    st.success("Traffic sent!")
    time.sleep(1)
    st.rerun()

if st.sidebar.button("Simulate Cloud Traffic"):
    simulate_traffic()

# --- FETCH DATA ---
try:
    headers = {"X-API-Key": API_KEY}
    response = requests.get(f"{API_URL}/stats", headers=headers, timeout=5)
    
    if response.status_code == 200:
        data = response.json()
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Secrets", data.get("total", 0))
        col2.metric("Emails Blocked", data.get("emails", 0))
        col3.metric("Phone Numbers", data.get("phones", 0))
        
        # Data Table
        st.subheader("Recent Activity Log (Secure)")
        logs = data.get("recent_logs", [])
        
        if logs:
            df = pd.DataFrame(logs)
            # Safe columns only
            # API returns: id, type, masked_id, timestamp
            desired_order = ["masked_id", "type", "timestamp", "id"]
            
            # Filter and Rename
            cols_to_show = [c for c in desired_order if c in df.columns]
            df = df[cols_to_show]
            
            # Rename for display
            rename_map = {"masked_id": "Masked ID", "type": "Type", "timestamp": "Timestamp", "id": "UUID"}
            df = df.rename(columns=rename_map)
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No activity recorded yet.")
            
    else:
        st.error(f"❌ Connection Failed: {response.status_code}")
        st.caption("Check your API Key and URL.")

except Exception as e:
    st.error(f"💥 Connection Error: {e}")
    st.caption("Is your Render service awake? It might take a minute to spin up.")
