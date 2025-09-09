import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests

# Constants
COMPANY_CSV = "companies.csv"
API_URL = "https://69259c07b830.ngrok-free.app "

# Streamlit page setup
st.set_page_config(page_title="Invoice Discounting Lead", layout="wide")
st.title("📊 Invoice Discounting Lead Dashboard")

# Load data
if os.path.exists(COMPANY_CSV):
    df = pd.read_csv(COMPANY_CSV, dtype={"phone": str})  # phone stays as string
else:
    st.error("❌ companies.csv not found. Please upload it.")
    st.stop()

# Map response codes to labels
response_map = {"1": "Interested", "2": "Not Interested"}
df["response_label"] = df["response"].fillna("No Reply").astype(str).map(response_map).fillna(df["response"].fillna("No Reply"))

# Show table with follow-up buttons
st.subheader("🏢 Company Data with Follow-Up")
for i, row in df.iterrows():
    cols = st.columns([3, 2, 2, 2])
    with cols[0]:
        st.write(f"**{row['company']}**")
    with cols[1]:
        st.write(row["phone"])
    with cols[2]:
        st.write(row["response_label"])
    with cols[3]:
        if row["response_label"] == "No Reply":
            if st.button(f"📩 Resend", key=f"resend_{i}"):
                try:
                    resp = requests.post(f"{API_URL}/resend", json={"company": row["company"], "phone": row["phone"]})
                    if resp.status_code == 200:
                        st.success(f"✅ Resent to {row['company']}")
                    else:
                        st.error(f"❌ Error: {resp.text}")
                except Exception as e:
                    st.error(f"⚠️ Could not connect: {e}")
        else:
            st.button("📩 Resend", key=f"resend_{i}", disabled=True)

st.divider()

# Start Lead button
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

# Refresh button
if st.button("🔄 Refresh Data"):
    df = pd.read_csv(COMPANY_CSV, dtype={"phone": str})
    st.experimental_rerun()

# Stats and Graphs
st.subheader("📈 Lead Analytics")
counts = df["response_label"].value_counts()

col1, col2 = st.columns([1, 2])

with col1:
    st.metric("Total Companies", len(df))
    st.metric("Interested", counts.get("Interested", 0))
    st.metric("Not Interested", counts.get("Not Interested", 0))
    st.metric("No Reply", counts.get("No Reply", 0))

with col2:
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(counts.index, counts.values, color=["green", "red", "gray"])
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha='center', va='bottom')
    ax.set_title("Lead Responses")
    ax.set_xlabel("Response Type")
    ax.set_ylabel("Count")
    plt.tight_layout()
    st.pyplot(fig)
