import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests

COMPANY_CSV = "companies.csv"

API_URL = "https://008aa14207a1.ngrok-free.app"
st.set_page_config(page_title="Invoice Discounting Lead", layout="wide")

st.title("📊 Invoice Discounting Lead Dashboard")

# Load data
if os.path.exists(COMPANY_CSV):
    df = pd.read_csv(COMPANY_CSV, dtype={"phone": str})  # phone as string (no commas)
else:
    st.error("❌ companies.csv not found. Please upload it.")
    st.stop()

# Show table
st.subheader("🏢 Company Data")
st.dataframe(df, use_container_width=True)

if st.button("🚀 Start Lead"):
    with st.spinner("Running lead..."):
        try:
            resp = requests.post(f"{API_URL}/run_lead")
            if resp.status_code == 200:
                st.success("✅ Lead started successfully!")
            else:
                st.error(f"❌ Error: {resp.text}")
        except Exception as e:
            st.error(f"⚠️ Could not connect to backend: {e}")

# Refresh button to reload CSV
if st.button("🔄 Refresh Data"):
    df = pd.read_csv(COMPANY_CSV, dtype={"phone": str})
    st.experimental_rerun()

# Stats and Graphs
st.subheader("📈 Lead Analytics")

if "response" in df.columns:
    # Response counts
    counts = df["response"].fillna("No Reply").value_counts()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Total Companies", len(df))
        st.metric("Interested (1)", counts.get("1", 0))
        st.metric("Not Interested (2)", counts.get("2", 0))
        st.metric("No Reply", counts.get("No Reply", 0))

    with col2:
        fig, ax = plt.subplots(figsize=(6,4))
        bars = ax.bar(counts.index, counts.values, color=["green", "red", "gray"])

        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
