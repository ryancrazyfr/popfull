import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

# Load sheet
sheet = client.open("POP_Log").worksheet("MuteStatus")
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Title
st.title("💋 Silk & Sin POP Dashboard")

# Overview Stats
col1, col2 = st.columns(2)
with col1:
    st.metric("✅ Active Users", len(df[df["Mute_Status"] == "Active"]))
with col2:
    st.metric("🔇 Muted Users", len(df[df["Mute_Status"] == "Muted"]))

# Table
st.subheader("📋 User Status Table")
st.dataframe(df, use_container_width=True)

# Chart
st.subheader("📊 Status Breakdown")
status_count = df["Mute_Status"].value_counts()
st.bar_chart(status_count)

# Filter by Username
st.subheader("🔍 Search User")
search = st.text_input("Enter username or ID")
if search:
    result = df[df["Username"].str.contains(search, case=False) | df["User_ID"].astype(str).str.contains(search)]
    st.write(result)

# Auto-refresh every 2 minutes
st.experimental_autorefresh(interval=120000, key="refresh")
