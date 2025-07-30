import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image
import numpy as np
from scipy.stats import norm
import datetime

# ------------------ Branding Header ------------------
st.image("your_combined_logo_filename.png", use_column_width=True)
st.markdown(
    """<h2 style='text-align: center; color: #6A5ACD;'>French Spirit - Laduree Dashboard</h2>
    <p style='text-align: center; color: gray;'>Powered by Taqtics</p>""",
    unsafe_allow_html=True
)

# ------------------ File Upload ------------------
uploaded_file = st.file_uploader(
    "Upload your CSV file (Exported for specific month)", 
    type=["csv"], 
    accept_multiple_files=False
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    # Ensure required columns exist
    required_columns = [
        "Country", "Store", "Audit Status", "Entity Id", 
        "Employee Name", "Result", "Submitted For"
    ]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()
    
    df['Result'] = pd.to_numeric(df['Result'], errors='coerce')

    # ------------- Extract Month from "Submitted For" column -------------
    # Assumes format like "01-Jul-25"
    def extract_month(dt):
        try:
            parsed_date = pd.to_datetime(dt, format='%d-%b-%y', errors='coerce')
            if pd.isnull(parsed_date):
                return None
            return parsed_date.strftime('%B %Y')
        except Exception:
            return None

    # Extract the most common (usually only) month in the data
    month_labels = df['Submitted For'].dropna().apply(extract_month)
    # Only consider first valid or mode (most common) if multiple months
    month_name = month_labels.mode()[0] if not month_labels.mode().empty else "Unknown Month"
    
    st.markdown(
        f"<h3 style='text-align: center; color: #20B2AA;'>Data for: {month_name}</h3>", 
        unsafe_allow_html=True
    )

    # ------------------ Sidebar Filters ------------------
    st.sidebar.header("Filters")
    countries = st.sidebar.multiselect(
        "Select Country", options=df['Country'].unique(), default=df['Country'].unique()
    )
    stores = st.sidebar.multiselect(
        "Select Store", options=df['Store'].unique(), default=df['Store'].unique()
    )

    filtered_df = df[
        (df['Country'].isin(countries)) &
        (df['Store'].isin(stores))
    ]

    # ------------------ Store-wise Count by Audit Status ------------------
    st.subheader("📊 Store-wise Count by Audit Status")
    selected_stores_bar = st.multiselect(
        "Select Store(s) for Audit Status Count Chart",
        options=sorted(df['Store'].dropna().unique()),
        default=sorted(df['Store'].dropna().unique())
    )
    filtered_status_df = df[df['Store'].isin(selected_stores_bar)]
    fig_store_audit_status = px.bar(
        filtered_status_df.groupby(['Store', 'Audit Status']).size().reset_index(name='Count'),
        x="Store",
        y="Count",
        color="Audit Status",
        barmode="stack",
        title="Store-wise Count by Audit Status",
        labels={"Count": "Number of Employees"}
    )
    fig_store_audit_status.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_store_audit_status)

    # ------------------ Country-specific Store Performance Chart ------------------
    st.subheader("🏆 Store Performance by Country")
    selected_country_perf = st.selectbox(
        "Select Country to View Store Performance",
        sorted(df['Country'].dropna().unique())
    )
    country_store_avg = df[df['Country'] == selected_country_perf].groupby('Store')['Result'].mean().reset_index()
    country_store_avg = country_store_avg.sort_values(by='Result', ascending=False)
    fig_country_perf = px.bar(
        country_store_avg,
        x='Store',
        y='Result',
        text='Result',
        title=f"Store Performance in {selected_country_perf} (High to Low)",
        labels={"Result": "Average Score"}
    )
    fig_country_perf.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig_country_perf.update_layout(xaxis_tickangle=-45, yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_country_perf)

    # ------------------ Country Drilldown ------------------
    st.subheader("Country-wise Bell Curve and Drilldown")
    selected_country = st.selectbox("Select Country for Drilldown", sorted(df['Country'].dropna().unique()))
    country_df = df[df['Country'] == selected_country]
    fig_country = px.histogram(
        country_df,
        x="Result",
        nbins=20,
        color="Audit Status",
        hover_data=["Entity Id", "Audit Status", "Employee Name"],
        labels={"Result": "Performance Score"},
        title=f"Performance Bell Curve for {selected_country}"
    )
    fig_country.update_layout(bargap=0.1)
    st.plotly_chart(fig_country)
    st.markdown(f"### Employees in {selected_country}")
    st.dataframe(country_df[[
        "Employee Name", "Store", "Entity Id", "Audit Status", "Result"
    ]].sort_values(by="Result", ascending=False))

    # ------------------ Store Drilldown ------------------
    st.subheader("Store-wise Bell Curve")
    selected_store = st.selectbox("Select Store", sorted(df['Store'].dropna().unique()))
    store_df = df[df['Store'] == selected_store]
    fig_store = px.histogram(
        store_df,
        x="Result",
        nbins=20,
        color="Audit Status",
        hover_data=["Country", "Entity Id", "Employee Name"],
        labels={"Result": "Performance Score"},
        title=f"Performance Bell Curve for {selected_store

