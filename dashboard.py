import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from scipy.stats import norm

# --- Branding Header ---
st.image("your_combined_logo_filename.png", use_container_width=True)
st.markdown(
    """<h2 style='text-align: center; color: #6A5ACD;'>French Spirit - Laduree Dashboard</h2>
    <p style='text-align: center; color: gray;'>Powered by Taqtics</p>""",
    unsafe_allow_html=True
)

def read_file(uploaded_file):
    try:
        return pd.read_csv(uploaded_file, sep=None, engine="python")  # auto-detect delimiter
    except Exception:
        try:
            return pd.read_excel(uploaded_file)
        except Exception:
            return None

def find_column(columns, target_names):
    col_lower = [c.lower() for c in columns]
    for t in target_names:
        if t.lower() in col_lower:
            return columns[col_lower.index(t.lower())]
    return None

uploaded_file = st.file_uploader("Upload your Performance CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    df = read_file(uploaded_file)
    if df is None:
        st.error("Unsupported file type! Please upload CSV or Excel.")
        st.stop()

    # Find required columns
    col_country = find_column(df.columns, ["Country"])
    col_store = find_column(df.columns, ["Store"])
    col_audit_status = find_column(df.columns, ["Audit Status"])
    col_entity_id = find_column(df.columns, ["Entity Id"])
    col_employee_name = find_column(df.columns, ["Employee Name"])
    col_result = find_column(df.columns, ["Result"])
    col_submitted_for = find_column(df.columns, ["Submitted For", "Submission Date"])

    required_cols = {
        "Country": col_country,
        "Store": col_store,
        "Audit Status": col_audit_status,
        "Entity Id": col_entity_id,
        "Employee Name": col_employee_name,
        "Result": col_result,
        "Submitted For": col_submitted_for
    }

    missing = [name for name, col in required_cols.items() if col is None]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    # Clean & restrict to required columns only
    df = df[list(required_cols.values())].copy()
    df[col_result] = pd.to_numeric(df[col_result], errors="coerce")
    df[col_submitted_for] = pd.to_datetime(df[col_submitted_for], errors="coerce")
    df = df.dropna(subset=[col_submitted_for])

    # Extract month for grouping
    df["Month"] = df[col_submitted_for].dt.to_period("M")

    # Keep first submission per employee per month
    df = df.sort_values(by=[col_employee_name, col_submitted_for])
    df = df.drop_duplicates(subset=["Month", col_employee_name], keep="first")

    # Month string for display
    month_str = df["Month"].astype(str).mode()
    month_str = month_str[0] if not month_str.empty else "Unknown Month"
    st.markdown(f"<h3 style='text-align: center; color: #20B2AA;'>Data for: {month_str}</h3>", unsafe_allow_html=True)

    # Sidebar filters
    st.sidebar.header("Filters")
    countries_selected = st.sidebar.multiselect("Select Country", options=df[col_country].unique(), default=df[col_country].unique())
    stores_selected = st.sidebar.multiselect("Select Store", options=df[col_store].unique(), default=df[col_store].unique())
    filtered_df = df[(df[col_country].isin(countries_selected)) & (df[col_store].isin(stores_selected))]

    # --- Existing Graphs ---
    st.subheader("📊 Store-wise Count by Audit Status")
    fig_store_audit_status = px.bar(
        filtered_df.groupby([col_store, col_audit_status]).size().reset_index(name="Count"),
        x=col_store,
        y="Count",
        color=col_audit_status,
        barmode="stack",
        title="Store-wise Count by Audit Status",
        labels={"Count": "Number of Employees"}
    )
    fig_store_audit_status.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig_store_audit_status)

    st.subheader("🏆 Store Performance by Country")
    selected_country_perf = st.selectbox("Select Country to View Store Performance", sorted(filtered_df[col_country].dropna().unique()))
    country_store_avg = filtered_df[filtered_df[col_country] == selected_country_perf].groupby(col_store)[col_result].mean().reset_index()
    country_store_avg = country_store_avg.sort_values(by=col_result, ascending=False)
    fig_country_perf = px.bar(
        country_store_avg,
        x=col_store,
        y=col_result,
        text=col_result,
        title=f"Store Performance in {selected_country_perf} (High to Low)",
        labels={col_result: "Average Score"}
    )
    fig_country_perf.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig_country_perf.update_layout(xaxis_tickangle=-45, yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_country_perf)

    # ... rest of your graphs remain unchanged ...

else:
    st.info("Please upload a CSV or Excel file to begin.")

