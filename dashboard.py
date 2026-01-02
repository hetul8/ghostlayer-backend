import streamlit as st
import redis
import pandas as pd
import plotly.express as px
import requests
import time
from faker import Faker

# Config
st.set_page_config(
    page_title="GhostLayer Admin",
    page_icon="👻",
    layout="wide",
)

st.title("👻 GhostLayer Real-Time Admin Panel")

# Initialize Faker
fake = Faker()

# API URL
API_BASE = "http://localhost:8000"

# Note: Since the backend is likely using FakeRedis (in-memory) if no real Redis is present,
# we cannot connect to 'redis://localhost' and see the same data from a different process.
# Therefore, we fetch data via the API's debug endpoint to ensure we see the actual server state.
# We still keep the Redis import as requested, but we rely on the API for data.

def get_data_from_api():
    try:
        response = requests.get(f"{API_BASE}/debug/keys")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch keys: {response.status_code}")
            return {}
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API. Is the server running?")
        return {}

def simulate_traffic():
    """Generates 5 random fake PII requests to the API."""
    with st.spinner("Injecting 5 fake entries..."):
        for _ in range(5):
            # Mix of emails and names
            if fake.boolean():
                text = f"My email is {fake.email()}"
            else:
                text = f"Call {fake.name()} at {fake.phone_number()}"
            
            try:
                requests.post(f"{API_BASE}/mask", json={"text": text})
            except:
                pass
    st.success("Traffic Simulated!")

# Sidebar
st.sidebar.header("Controls")
refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 1, 10, 2)
if st.sidebar.button("Simulate Traffic"):
    simulate_traffic()
    time.sleep(0.5) # Wait a bit for server to process
    st.rerun()

# Main Loop Area
placeholder = st.empty()

# We use a loop for auto-refresh if run with `streamlit run`
# calling st.rerun() inside the loop or using st.empty container.
# Here we will use the st.empty() approach with a sleep loop, 
# but Streamlit's way is often just to let the script rerun top-to-bottom.
# To do "live feed", we can use `st.rerun()` at the end with a sleep.

# Fetch Data
data = get_data_from_api()

# Metrics
total_secrets = len(data)
emails_blocked = sum(1 for k in data.keys() if "[EMAIL" in k)
phones_blocked = sum(1 for k in data.keys() if "[PHONE" in k)
persons_blocked = sum(1 for k in data.keys() if "[PERSON" in k) # Bonus metric

# Columns
col1, col2, col3 = st.columns(3)
col1.metric("Total Secrets Protected", total_secrets)
col2.metric("Emails Blocked", emails_blocked)
col3.metric("Phone Numbers Blocked", phones_blocked)

# Data Table
st.subheader("Live Intercepted Keys")
if total_secrets > 0:
    # Create DataFrame
    df = pd.DataFrame(list(data.items()), columns=["Masked ID", "Real Data"])
    
    # Hide Real Data for Admin Privacy
    # Masking: sally@test.com -> s****@test.com
    def mask_real_val(val):
        if "@" in val: # Simple email check
            parts = val.split("@")
            if len(parts[0]) > 1:
                return parts[0][0] + "****" + "@" + parts[1]
            return "****@" + parts[1]
        elif len(val) > 4: # Phone or Name
            return val[:2] + "****" + val[-2:]
        return "****"
        
    df["Real Data"] = df["Real Data"].apply(mask_real_val)
    
    st.dataframe(df, use_container_width=True)
else:
    st.info("No secrets detected yet. Go to ChatGPT or Click 'Simulate Traffic'.")

# Auto Refresh logic
time.sleep(refresh_rate)
st.rerun()
