import os
import json
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials



# 🔑 Load Google credentials from environment variable
creds_dict = json.loads(os.environ["GOOGLE_JSON"])  # or GOOGLE_CREDS, depending on what you set
creds = Credentials.from_service_account_info(creds_dict, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])

# Connect to Google Sheets
client = gspread.authorize(creds)
spreadsheet = client.open("pop_submissions")   # <-- Change to your actual Google Sheet name
sheet = spreadsheet.worksheet("MuteStatus")   # <-- Change to your actual worksheet name

# Load data into DataFrame
data = sheet.get_all_records()
df = pd.DataFrame(data)

# 🎨 Dashboard UI
st.set_page_config(page_title="Silk & Sin Dashboard", page_icon="💋", layout="wide")

st.title("💋 Silk & Sin POP Dashboard")

# 📊 Overview Stats
col1, col2 = st.columns(2)
with col1:
    st.metric("✅ Active Users", len(df[df["Mute_Status"] == "Active"]))
with col2:
    st.metric("🔇 Muted Users", len(df[df["Mute_Status"] == "Muted"]))

# 📑 Full Table
st.subheader("📋 User Status Table")
st.dataframe(df, use_container_width=True)

# Optional: filter/search
st.subheader("🔍 Search Users")
search = st.text_input("Enter username or ID")
if search:
    filtered = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]
    st.dataframe(filtered, use_container_width=True)
