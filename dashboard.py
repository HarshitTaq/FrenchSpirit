import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np
from scipy.stats import norm

# ------------------ Branding Header ------------------
st.image("your_combined_logo_filename.png", use_column_width=True)
st.markdown(
    """<h2 style='text-align: center; color: #6A5ACD;'>French Spirit - Laduree Dashboard</h2>
    <p style='text-align: center; color: gray;'>Powered by Taqtics</p>""",
    unsafe_allow_html=True
)

# ------------------ File Upload and Reading ------------------
uploaded_file = st.file_uploader(
    "Upload your CSV file (Performance data for a month)", type=["csv"]
)

if uploaded_file is not None:
    # Attempt to read CSV file with flexible engine, handle common delimiters
    delimiter = st.selectbox("Select CSV delimiter", [",", ";", "\t"], index=0)
    try:
        df = pd.read_csv(uploaded_file, sep=delimiter, engine="python", encoding="utf-8")
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
        st.stop()

    # Required columns including 'Submitted For' for datetime
    required_cols = [
        "Country", "Store", "Audit Status", "Entity Id", 
        "Employee Name", "Result", "Submitted For"
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"Missing required columns in your file: {', '.join(missing_cols)}")
        st.stop()

    # Convert 'Result' to numeric safely
    df['Result'] = pd.to_numeric(df['Result'], errors='coerce')

    # Parse 'Submitted For' into datetime
    df['Submitted For'] = pd.to_datetime(df['Submitted For'], errors='coerce', dayfirst=True)

    # Drop rows where 'Submitted For' is NaT after parsing
    df = df.dropna(subset=['Submitted For'])

    # Sort by Employee and Submission date, keep only first submission per employee
    df = df.sort_values(['Employee Name', 'Submitted For'])
    df = df.drop_duplicates(subset=['Employee Name'], keep='first')

    # Extract month-year for display from 'Submitted For' column using mode (most common)
    month_display = df['Submitted For'].dt.strftime('%B %Y').mode()
    month_display = month_display[0] if not month_display.empty else "Unknown Month"

    st.markdown(
        f"<h3 style='text-align: center; color: #20B2AA;'>Data for: {month_display}</h3>", 
        unsafe_allow_html=True
    )

    # ------------------ Sidebar Filters ------------------
    st.sidebar.header("Filters")
    countries = st.sidebar.multiselect("Select Country", options=df['Country'].unique(), default=df['Country'].unique())
    stores = st.sidebar.multiselect("Select Store", options=df['Store'].unique(), default=df['Store'].unique())

    filtered_df = df[(df['Country'].isin(countries)) & (df['Store'].isin(stores))]

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
    st.dataframe(
        country_df[["Employee Name", "Store", "Entity Id", "Audit Status", "Result"]]
        .sort_values(by="Result", ascending=False)
    )

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
        title=f"Performance Bell Curve for {selected_store}"
    )
    fig_store.update_layout(bargap=0.1)
    st.plotly_chart(fig_store)

    # ------------------ Probability Distribution Chart ------------------
    st.subheader("Probability Density of Performance Scores")
    mean_score = filtered_df['Result'].mean()
    std_dev = filtered_df['Result'].std()
    if not filtered_df['Result'].isnull().all():
        x = np.linspace(filtered_df['Result'].min(), filtered_df['Result'].max(), 500)
        pdf_y = norm.pdf(x, mean_score, std_dev)
        fig_pdf = go.Figure()
        fig_pdf.add_trace(go.Scatter(x=x, y=pdf_y, mode='lines', name='PDF'))
        fig_pdf.add_vline(
            x=mean_score, line_dash='dash', line_color='green',
            annotation_text='Mean', annotation_position='top left'
        )
        fig_pdf.update_layout(
            title='Probability Density Function (PDF) of Performance Scores',
            xaxis_title='Performance Score',
            yaxis_title='Probability Density'
        )
        st.plotly_chart(fig_pdf)
    st.markdown(f"**Mean Score:** {mean_score:.2f}  \n**Standard Deviation:** {std_dev:.2f}")

    # ------------------ Country vs Score by Audit Status ------------------
    st.subheader("Score Distribution by Country and Audit Status")
    fig_country_status = px.strip(
        filtered_df,
        x="Country",
        y="Result",
        color="Audit Status",
        hover_data=["Employee Name", "Store", "Entity Id"],
        stripmode="overlay",
        labels={"Result": "Performance Score"},
        title="Performance Scores by Country Grouped by Audit Status"
    )
    fig_country_status.update_layout(yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_country_status)

else:
    st.info("Please upload a CSV file to begin.")
