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
    delimiter = st.selectbox("Select CSV delimiter", [",", ";", "\t", "|"], index=0)
    try:
        df = pd.read_csv(uploaded_file, sep=delimiter, engine="python", encoding="utf-8")
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
        st.stop()

    # Find columns regardless of upper/lower/space/underscore differences
    def find_column(cols, target):
        colmap = {c.lower().replace(" ", "").replace("_", ""): c for c in cols}
        return colmap.get(target.lower().replace(" ", "").replace("_", ""))
    # Mapping expected fields in code to actual CSV headers
    expected = {
        "Country": "Country",
        "Store": "Store",
        "Audit Status": "Audit Status",
        "Entity Id": "Entity Id",
        "Employee Name": "Employee Name",
        "Result": "Result",
        "Submitted For": "Submitted For"
    }
    for k in expected:
        col = find_column(df.columns, k)
        if not col:
            st.error(f"Missing required column: {k}")
            st.stop()
        expected[k] = col  # Remap in case of minor header diff

    # Convert Result to numeric safely
    df[expected['Result']] = pd.to_numeric(df[expected['Result']], errors='coerce')

    # Parse 'Submitted For' into datetime (try multiple date formats for robustness)
    for fmt in ["%d-%b-%y", "%d %B %Y", "%d/%m/%Y", "%d %b %Y", "%d-%B-%Y"]:
        df[expected['Submitted For']] = pd.to_datetime(
            df[expected['Submitted For']], format=fmt, errors='coerce'
        )
        # If enough dates were successfully parsed, break
        if df[expected['Submitted For']].notnull().sum() > len(df) * 0.5:
            break

    # Drop rows where Submitted For did not parse
    df = df.dropna(subset=[expected['Submitted For']])

    # Deduplicate: Keep only FIRST submission per Country+Store+Employee for the month
    df = df.sort_values([expected["Country"], expected["Store"], expected["Employee Name"], expected["Submitted For"]])
    df = df.drop_duplicates(
        subset=[expected["Country"], expected["Store"], expected["Employee Name"]],
        keep="first"
    )

    # Extract month display (mode or first valid)
    month_display = df[expected['Submitted For']].dt.strftime('%B %Y').mode()
    month_display = month_display[0] if not month_display.empty else "Unknown Month"
    st.markdown(
        f"<h3 style='text-align: center; color: #20B2AA;'>Data for: {month_display}</h3>", 
        unsafe_allow_html=True
    )

    # Use remapped columns for rest of app
    # All column references are through expected[...] (ensures column found)
    st.sidebar.header("Filters")
    countries = st.sidebar.multiselect(
        "Select Country", options=df[expected['Country']].unique(),
        default=df[expected['Country']].unique()
    )
    stores = st.sidebar.multiselect(
        "Select Store", options=df[expected['Store']].unique(),
        default=df[expected['Store']].unique()
    )
    filtered_df = df[
        (df[expected['Country']].isin(countries)) &
        (df[expected['Store']].isin(stores))
    ]

    # ------------------ Store-wise Count by Audit Status ------------------
    st.subheader("📊 Store-wise Count by Audit Status")
    selected_stores_bar = st.multiselect(
        "Select Store(s) for Audit Status Count Chart",
        options=sorted(df[expected['Store']].dropna().unique()),
        default=sorted(df[expected['Store']].dropna().unique())
    )
    filtered_status_df = df[df[expected['Store']].isin(selected_stores_bar)]
    fig_store_audit_status = px.bar(
        filtered_status_df.groupby(
            [expected['Store'], expected['Audit Status']]
        ).size().reset_index(name='Count'),
        x=expected['Store'],
        y="Count",
        color=expected['Audit Status'],
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
        sorted(df[expected['Country']].dropna().unique())
    )
    country_store_avg = df[df[expected['Country']] == selected_country_perf] \
        .groupby(expected['Store'])[expected['Result']].mean().reset_index()
    country_store_avg = country_store_avg.sort_values(by=expected['Result'], ascending=False)
    fig_country_perf = px.bar(
        country_store_avg,
        x=expected['Store'],
        y=expected['Result'],
        text=expected['Result'],
        title=f"Store Performance in {selected_country_perf} (High to Low)",
        labels={expected['Result']: "Average Score"}
    )
    fig_country_perf.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig_country_perf.update_layout(xaxis_tickangle=-45, yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_country_perf)

    # ------------------ Country Drilldown ------------------
    st.subheader("Country-wise Bell Curve and Drilldown")
    selected_country = st.selectbox("Select Country for Drilldown", sorted(df[expected['Country']].dropna().unique()))
    country_df = df[df[expected['Country']] == selected_country]
    fig_country = px.histogram(
        country_df,
        x=expected['Result'],
        nbins=20,
        color=expected['Audit Status'],
        hover_data=[expected['Entity Id'], expected['Audit Status'], expected['Employee Name']],
        labels={expected['Result']: "Performance Score"},
        title=f"Performance Bell Curve for {selected_country}"
    )
    fig_country.update_layout(bargap=0.1)
    st.plotly_chart(fig_country)

    st.markdown(f"### Employees in {selected_country}")
    st.dataframe(
        country_df[
            [expected["Employee Name"], expected["Store"], expected["Entity Id"], expected["Audit Status"], expected["Result"]]
        ].sort_values(by=expected["Result"], ascending=False)
    )

    # ------------------ Store Drilldown ------------------
    st.subheader("Store-wise Bell Curve")
    selected_store = st.selectbox("Select Store", sorted(df[expected['Store']].dropna().unique()))
    store_df = df[df[expected['Store']] == selected_store]
    fig_store = px.histogram(
        store_df,
        x=expected['Result'],
        nbins=20,
        color=expected['Audit Status'],
        hover_data=[expected['Country'], expected['Entity Id'], expected['Employee Name']],
        labels={expected['Result']: "Performance Score"},
        title=f"Performance Bell Curve for {selected_store}"
    )
    fig_store.update_layout(bargap=0.1)
    st.plotly_chart(fig_store)

    # ------------------ Probability Distribution Chart ------------------
    st.subheader("Probability Density of Performance Scores")
    mean_score = filtered_df[expected['Result']].mean()
    std_dev = filtered_df[expected['Result']].std()
    if not filtered_df[expected['Result']].isnull().all():
        x = np.linspace(
            filtered_df[expected['Result']].min(),
            filtered_df[expected['Result']].max(),
            500
        )
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
        x=expected['Country'],
        y=expected['Result'],
        color=expected['Audit Status'],
        hover_data=[expected['Employee Name'], expected['Store'], expected['Entity Id']],
        stripmode="overlay",
        labels={expected['Result']: "Performance Score"},
        title="Performance Scores by Country Grouped by Audit Status"
    )
    fig_country_status.update_layout(yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig_country_status)

else:
    st.info("Please upload a CSV file to begin.")
