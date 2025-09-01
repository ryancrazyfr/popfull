import os
import json
import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

# 🔑 Load Google credentials from environment
creds_dict = json.loads(os.environ["GOOGLE_JSON"])
creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
)

# 📂 Connect to Google Sheets
client = gspread.authorize(creds)
spreadsheet = client.open("POP Submissions")        # Your sheet name
sheet = spreadsheet.worksheet("MuteStatus")         # Your tab name

# 📊 Load data into DataFrame
data = sheet.get_all_records()
df = pd.DataFrame(data)

# 🎨 Dashboard UI
st.set_page_config(page_title="Silk & Sin Dashboard", page_icon="💋", layout="wide")
st.title("💋 Silk & Sin POP Dashboard")

# 📝 Check if sheet has data
if df.empty:
    st.warning("⚠️ No data found in the Google Sheet yet. Please add some entries.")
else:
    # Normalize headers just in case (spaces → underscores)
    df.columns = df.columns.str.strip().str.replace(" ", "_")

    # 📌 Overview Stats
    col1, col2 = st.columns(2)
    with col1:
        st.metric("✅ Active Users", len(df[df["Mute_Status"] == "Active"]))
    with col2:
        st.metric("❌ Muted Users", len(df[df["Mute_Status"] == "Muted"]))

    # 📅 Latest actions
    st.subheader("🕒 Recent Actions")
    if "Timestamp" in df.columns:
        df_sorted = df.sort_values(by="Timestamp", ascending=False)
        st.dataframe(df_sorted.head(10), use_container_width=True)
    else:
        st.info("No Timestamp column found in sheet.")

    # 🔍 Search & Filter
    st.subheader("🔎 Search Users")
    search = st.text_input("Enter Username or User_ID")
    if search:
        filtered = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
        st.dataframe(filtered, use_container_width=True)

    # 📋 Full Table
    st.subheader("📋 Full User Status Table")
    st.dataframe(df, use_container_width=True)
