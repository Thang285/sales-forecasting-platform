import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.graph_objects as go
import os
from streamlit_autorefresh import st_autorefresh
import altair as alt
import requests
import streamlit.components.v1 as components
from streamlit.components.v1 import html
alt.data_transformers.disable_max_rows()
# Database connection details
DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
DB_NAME = os.environ.get('POSTGRES_DB', 'your_database')
DB_USER = os.environ.get('POSTGRES_USER', 'your_user')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'your_password')

def connect_to_db():
    try:
        return psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
    except psycopg2.Error as e:
        st.error(f"Error connecting to database: {e}")
        return None

def fetch_data(conn, query):
    try:
        return pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def create_line_chart(df):
    if df.empty:
        return None
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    sales = df.groupby('InvoiceDate')['SaleAmount'].sum().reset_index()
    return px.line(sales, x='InvoiceDate', y='SaleAmount', title='Sales Over Time')

def render_line_card(df, title="Sales Over Time", color="#ffffff"):
    chart = (
    alt.Chart(df)
    .mark_line()
    .encode(
        x=alt.X("InvoiceDate:T", title="Date"),
        y=alt.Y("SaleAmount:Q", title="Sales"),
        tooltip=["InvoiceDate", "SaleAmount"]
    )
    .properties(
        width="container",  # 🟢 Important: Make it responsive
        height=300
    )
    .configure_view(
        stroke=None
    )
    )

    chart_html = chart.to_html()  # ✅ works without vegafusion

    full_html = f"""
    <div style="
        background-color: {color};
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        font-family: 'Segoe UI', sans-serif;">
        <h4 style="margin: 0 0 1rem 0;">{title}</h4>
        {chart_html}
    </div>
    """

    html(full_html, height=500)

def render_cumulative_card(df, title="📊 Cumulative Sales Over Time", color="#ffffff"):
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['InvoiceDay'] = pd.to_datetime(df['InvoiceDate'].dt.date)

    daily_sales = df.groupby('InvoiceDay')['SaleAmount'].sum().reset_index()
    daily_sales['CumulativeSales'] = daily_sales['SaleAmount'].cumsum()

    chart = (
        alt.Chart(daily_sales)
        .mark_line()
        .encode(
            x=alt.X("InvoiceDay:T", title="Date"),
            y=alt.Y("CumulativeSales:Q", title="Cumulative Sales"),
            tooltip=["InvoiceDay", "CumulativeSales"]
        )
        .properties(
            width="container",
            height=300
        )
        .configure_view(stroke=None)
    )

    chart_html = chart.to_html()

    full_html = f"""
    <div style="
        background-color: {color};
        padding: 1.5rem;
        border-radius: 18px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
        margin-bottom: 2rem;
        font-family: 'Segoe UI', sans-serif;">
        <h4 style="margin: 0 0 1rem 0;">{title}</h4>
        {chart_html}
    </div>
    """

    html(full_html, height=500)

    
def create_donut_chart(df):
    alt.data_transformers.disable_max_rows()

    # ✅ Aggregate and compute percent
    channel_sales = df.groupby('MarketingChannel')['SaleAmount'].sum().reset_index()
    total = channel_sales['SaleAmount'].sum()
    channel_sales['Percent'] = channel_sales['SaleAmount'] / total
    title="📊 Marketing Channel Share"
    color="#ffffff"
    # ✅ Create the donut chart
    chart = alt.Chart(channel_sales).mark_arc(innerRadius=60).encode(
        theta=alt.Theta(field="SaleAmount", type="quantitative"),
        color=alt.Color(field="MarketingChannel", type="nominal", legend=alt.Legend(title="Channel")),
        tooltip=[alt.Tooltip("MarketingChannel:N"), 
                 alt.Tooltip("SaleAmount:Q", format=",.2f"), 
                 alt.Tooltip("Percent:Q", format=".1%")]
    ).properties(
        width=350,
        height=350,
        title=title
    ).configure_title(
        anchor="start",
        fontSize=16,
        fontWeight="bold"
    )

    chart_html = chart.to_html()

    full_html = f"""
    <div style="
        background-color: {color};
        padding: 1.5rem;
        border-radius: 18px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
        margin-bottom: 2rem;
        font-family: 'Segoe UI', sans-serif;
        text-align: center;">
        {chart_html}
    </div>
    """

    html(full_html, height=450)

def create_bar_chart(df):
    stage_counts = df.groupby('OpportunityStage')['OpportunityAmount'].count().reset_index()
    stage_counts.columns = ['OpportunityStage', 'OpportunityCount']
    title="📊 Opportunities by Stage"
    color="#ffffff"
    # Altair chart
    chart = alt.Chart(stage_counts).mark_bar().encode(
        x=alt.X("OpportunityStage:N", title="Stage"),
        y=alt.Y("OpportunityCount:Q", title="Count"),
        tooltip=["OpportunityStage", "OpportunityCount"]
    ).properties(
        height=280,
        width="container",
        title=title
    ).configure_title(
        anchor="start",
        fontSize=16,
        fontWeight="bold"
    )

    chart_html = chart.to_html()
    full_html = f"""
    <div style="
        background-color: {color};
        padding: 1.5rem;
        border-radius: 18px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
        margin-bottom: 2rem;
        font-family: 'Segoe UI', sans-serif;
        text-align: center;">
        {chart_html}
    </div>
    """

    html(full_html, height=450)

def create_size_chart(df):
    if df.empty:
        return None
    size_sales = df.groupby('OpportunitySize')['SaleAmount'].sum().reset_index()
    return px.bar(size_sales, x='OpportunitySize', y='SaleAmount', title='Sales by Opportunity Size')

def create_indicator(value, title, color):
     
    fig = go.Figure(go.Indicator(
        mode="number",
        value=value,
        title={'text': f"<b>{title}</b>", 'font': {'size': 16}},
        number={'prefix': '$', 'font': {'size': 28}},
        domain={'x': [0, 1], 'y': [0, 1]},
        delta={'reference': 0},
    ))

    fig.update_layout(
        paper_bgcolor=color,
        plot_bgcolor=color,
        height=200,
        margin=dict(l=10, r=10, t=40, b=20),
        font=dict(color='black'),
        autosize=True,
        shapes=[
            dict(
                type="rect",
                x0=0, x1=1,
                y0=0, y1=1,
                line=dict(color="rgba(0,0,0,0)"),
                fillcolor=color,
                layer="below"
            )
        ]
    )

    return fig
def render_stat_card(title, value, color):
    html = f"""
    <div style="
        background-color: {color};
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        text-align: center;
        font-family: 'Segoe UI', sans-serif;
        margin-bottom: 1.5rem;">
        <h4 style="margin: 0; font-size: 16px; color: #444;">{title}</h4>
        <h2 style="margin: 0; font-size: 32px; color: #222;">{value}</h2>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def format_number(value):
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.2f}K"
    else:
        return f"${value:,.2f}"

def create_cumulative_chart(df):
    if df.empty:
        return None

    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])

    # ✅ Group by DATE (not full datetime)
    df['InvoiceDay'] = df['InvoiceDate'].dt.date

    daily_sales = df.groupby('InvoiceDay')['SaleAmount'].sum().reset_index()
    daily_sales['CumulativeSales'] = daily_sales['SaleAmount'].cumsum()

    fig = px.line(
        daily_sales,
        x='InvoiceDay',
        y='CumulativeSales',
        title='📈 Cumulative Sales Over Time',
        labels={'InvoiceDay': 'Date', 'CumulativeSales': 'Cumulative Sales'}
    )

    fig.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=40, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def create_sales_by_country_chart(df):
    if df.empty:
        return None
    country_sales = df.groupby('Store')['SaleAmount'].sum().reset_index()
    return px.bar(country_sales, x='Store', y='SaleAmount', title='Sales Per Country')


def main():
    st.set_page_config(page_title='Sales Dashboard Of Binh Đoàn Bóng Tối', layout='wide')
    st.markdown("""
    <style>
    .card {
        background-color: #ffffff;
        padding: 1.75rem;
        border-radius: 20px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
        margin-bottom: 2rem;
        transition: all 0.2s ease-in-out;
    }

    /* Optional: slight hover effect */
    .card:hover {
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)
    st.title("Sales Dashboard Of Binh Đoàn Bóng Tối")
    st_autorefresh(interval=30 * 1000, key="auto_refresh")

    if st.sidebar.button("🔁 Refresh now"):
        st.rerun()

    conn = connect_to_db()
    if not conn:
        return

    # Fetch sales data
    sales_query = """
        SELECT
            "InvoiceDate",
            SUM("Quantity" * "UnitPrice") AS "SaleAmount",
            CASE 
            WHEN random() < 0.3 THEN 'Organic'
            ELSE 'Paid'
            END AS "MarketingChannel",
            "Country" AS "Store"
        FROM online_retail_data
        GROUP BY "InvoiceDate", "Country"
        ORDER BY "InvoiceDate"
    """
    sales_df = fetch_data(conn, sales_query)

    # Simulate opportunity data
    opportunity_query = """
        SELECT
            "InvoiceDate",
            CASE
                WHEN random() < 0.2 THEN 'Lead'
                WHEN random() < 0.5 THEN 'Qualify'
                WHEN random() < 0.7 THEN 'Proposal'
                WHEN random() < 0.9 THEN 'Finalize'
                ELSE 'Won'
            END AS "OpportunityStage",
            (random() * 100000) AS "OpportunityAmount",
            CASE
                WHEN random() < 0.3 THEN '20K or less'
                WHEN random() < 0.6 THEN '20K to 40K'
                WHEN random() < 0.8 THEN '40K to 60K'
                ELSE 'More than 60K'
            END AS "OpportunitySize"
        FROM online_retail_data
    """
    opp_df = fetch_data(conn, opportunity_query)

    if conn:
        conn.close()

    # Sidebar filters
    st.sidebar.header("Filters")
    if not sales_df.empty:
        sales_df['InvoiceDate'] = pd.to_datetime(sales_df['InvoiceDate'])
        
        # Add "All Stores" option
        stores = sales_df['Store'].unique().tolist()
        stores.insert(0, "All Stores")  # Prepend "All Stores"
        selected_store = st.sidebar.selectbox("Store", stores)

        # Date range
        min_date = sales_df['InvoiceDate'].min().date()
        max_date = sales_df['InvoiceDate'].max().date()
        start_date = st.sidebar.date_input("Start Date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("End Date", max_date, min_value=min_date, max_value=max_date)

        # Filter based on store selection
        if selected_store == "All Stores":
            filtered_sales = sales_df[
                (sales_df['InvoiceDate'].dt.date >= start_date) &
                (sales_df['InvoiceDate'].dt.date <= end_date)
            ]
        else:
            filtered_sales = sales_df[
                (sales_df['Store'] == selected_store) &
                (sales_df['InvoiceDate'].dt.date >= start_date) &
                (sales_df['InvoiceDate'].dt.date <= end_date)
            ]
    else:
        filtered_sales = pd.DataFrame()

    # Metrics
    st.header("Overview")
    col1, col2, col3 = st.columns(3)
    if not filtered_sales.empty:
        total_sales = filtered_sales['SaleAmount'].sum()
        with col1:
            render_stat_card("💰 Total Sales", format_number(total_sales), "#e6f7ff")

    if not opp_df.empty:
        total_opp = opp_df['OpportunityAmount'].sum()
        avg_opp = opp_df['OpportunityAmount'].mean()
        
        with col2:
            render_stat_card("📈 Total Opportunities", format_number(total_opp), "#e6ffe6")

        with col3:
            render_stat_card("📊 Avg. Opportunity Size", format_number(avg_opp), "#fff3e6")

    # Charts
    st.header("Sales & Opportunities")
    sales_chart_df = filtered_sales.groupby('InvoiceDate')['SaleAmount'].sum().reset_index()
    render_line_card(sales_chart_df)
    
    render_cumulative_card(filtered_sales)

    st.header("Marketing and Opportunity Analysis")
    col5, col6 = st.columns(2)
    with col5:
        donut_chart = create_donut_chart(filtered_sales)
    with col6:
        bar_chart = create_bar_chart(opp_df)

    # size_chart = create_size_chart(opp_df)
    # if size_chart:
    #     st.plotly_chart(size_chart, use_container_width=True)
    
    st.header("Sales Per Country")
    sales_country_chart = create_sales_by_country_chart(filtered_sales)
    if sales_country_chart:
        st.plotly_chart(sales_country_chart, use_container_width=True)
    st.header("Forcasting Using LSTM Model (Only appeart when click '📈 Get Forecast')")
    st.sidebar.header("🔧 Forecast Settings")
    # User inputs
    country = st.sidebar.selectbox("Select Country", ["United Kingdom", "France", "Germany"])
    freq = st.sidebar.selectbox("Select Time Unit", ["D", "M", "Y"])
    periods = st.sidebar.slider("Forecast Periods", min_value=7, max_value=60, step=1, value=30)

    if st.sidebar.button("📈 Get Forecast"):
        with st.spinner("Fetching forecast from API..."):
            payload = {
                "country": country,
                "freq": freq,
                "periods": periods
            }

            try:
                response = requests.post("https://api.willdzai04.asia/predict", json=payload)
                response.raise_for_status()
                forecast_data = response.json()
                forecast_df = pd.DataFrame(forecast_data)

                st.subheader(f"Forecasted Sales for {country} ({freq}, next {periods})")
                fig = px.line(forecast_df, x="Date", y="Predicted Sales", title="📈 Forecast from Prophet")
                st.plotly_chart(fig, use_container_width=True)

            except requests.exceptions.RequestException as e:
                st.error(f"Failed to get forecast: {e}")



if __name__ == "__main__":
    main()
