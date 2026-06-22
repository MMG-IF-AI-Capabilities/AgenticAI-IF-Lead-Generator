import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL")
COMPANY_CSV = "qualified_company_list.csv"
# Initialize session state for inline status messages
if "sent_status" not in st.session_state:
    st.session_state["sent_status"] = {}


# Streamlit page setup
st.set_page_config(page_title="Invoice Discounting Lead", layout="wide")
st.title("📊 Invoice Discounting Lead Dashboard")

# Load data
if os.path.exists(COMPANY_CSV) and os.path.getsize(COMPANY_CSV) > 0:
    df = pd.read_csv(COMPANY_CSV, dtype={"phone": str})  # Keep phone as string
else:
    df = pd.DataFrame(columns=[
        "companyNumber", "companyName", "chUrl", "cfps_score", "qualitative_narrative",
        "final_qualification", "domain", "phone", "emails", "response", "turnover",
        "funding_type", "recommended_product", "slot", "stage"
    ])
    st.info("ℹ️ The company list is empty. Please upload or run the lead generation process.")


st.subheader("🏢 Company Data with Follow-Up")
if not df.empty:

    cols = st.columns([3, 2, 2, 3])
    cols[0].write("**Company Name**")
    cols[1].write("**Phone**")
    cols[2].write("**Response**")
    cols[3].write("**Action**")

    for i, row in df.iterrows():
        cols = st.columns([3, 2, 2, 3])
        with cols[0]:
            st.write(row["companyName"])
        with cols[1]:
            st.write(row["phone"])
        with cols[2]:
            st.write(row["response"] or "No Response")
        with cols[3]:
            btn_key = f"resend_{i}"
            status_text = st.session_state["sent_status"].get(btn_key, "")
            with st.container():
                is_disabled = (row["response"] != "No Response" and pd.notna(row["response"]))
                if st.button("📩 Resend", key=btn_key, disabled=is_disabled):
                    try:
                        resp = requests.post(
                            f"{API_URL}/resend",
                            json={"company": row["companyName"], "phone": row["phone"]}
                        )
                        if resp.status_code == 200:
                            st.session_state["sent_status"][btn_key] = "✅ Message Resent"
                        else:
                            st.session_state["sent_status"][btn_key] = f"❌ Error: {resp.text}"
                    except Exception as e:
                        st.session_state["sent_status"][btn_key] = f"⚠️ Could not connect: {e}"
                # Show the status inline
                if status_text:
                    st.write(status_text)
else:
    st.write("No company data available yet.")

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
    st.experimental_rerun()

# Stats and Graphs
st.subheader("📈 Lead Analytics")
if not df.empty:
    counts = df["response"].fillna("No Response").value_counts()
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Total Companies", len(df))
        st.metric("Interested", counts.get("Interested", 0))
        st.metric("Not Interested", counts.get("Not Interested", 0))
        st.metric("No Response", counts.get("No Response", 0))
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
else:
    st.info("No analytics to display yet.")
