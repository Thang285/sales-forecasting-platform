import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.graph_objects as go
import os
import requests

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

def create_donut_chart(df):
    if df.empty:
        return None
    channel_sales = df.groupby('MarketingChannel')['SaleAmount'].sum().reset_index()
    return px.pie(channel_sales, names='MarketingChannel', values='SaleAmount', hole=0.3)

def create_bar_chart(df):
    if df.empty:
        return None
    stage_counts = df.groupby('OpportunityStage')['OpportunityAmount'].count().reset_index()
    return px.bar(stage_counts, x='OpportunityStage', y='OpportunityAmount', title='Opportunities by Stage')

def create_size_chart(df):
    if df.empty:
        return None
    size_sales = df.groupby('OpportunitySize')['SaleAmount'].sum().reset_index()
    return px.bar(size_sales, x='OpportunitySize', y='SaleAmount', title='Sales by Opportunity Size')

def create_indicator(value, title, color):
    return go.Figure(go.Indicator(
        mode="number",
        value=value,
        title={'text': f"<b>{title}</b>", 'font': {'size': 16}},
        number={'prefix': '$', 'font': {'size': 28}},
        domain={'x': [0, 1], 'y': [0, 1]},
        delta={'reference': 0},
    )).update_layout(
        paper_bgcolor=color,
        height=200,
        margin=dict(l=20, r=20, t=40, b=0)
    )

def create_cumulative_chart(df):
    if df.empty:
        return None
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    sales = df.groupby('InvoiceDate')['SaleAmount'].sum().reset_index()
    sales['CumulativeSales'] = sales['SaleAmount'].cumsum()
    return px.line(sales, x='InvoiceDate', y='CumulativeSales', title='Cumulative Sales Over Time')

def create_sales_by_country_chart(df):
    if df.empty:
        return None
    country_sales = df.groupby('Store')['SaleAmount'].sum().reset_index()
    return px.bar(country_sales, x='Store', y='SaleAmount', title='Sales Per Country')


def main():
    st.set_page_config(page_title='Sales Dashboard', layout='wide')
    st.title("Sales Dashboard")

    conn = connect_to_db()
    if not conn:
        return

    # Fetch sales data
    sales_query = """
        SELECT
            "InvoiceDate",
            SUM("Quantity" * "UnitPrice") AS "SaleAmount",
            'Organic' AS "MarketingChannel",
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
        col1.plotly_chart(create_indicator(total_sales, '💰 Total Sales', '#e6f7ff'), use_container_width=True)
    if not opp_df.empty:
        total_opp = opp_df['OpportunityAmount'].sum()
        avg_opp = opp_df['OpportunityAmount'].mean()
        col2.plotly_chart(create_indicator(total_opp, '📈 Total Opportunities', '#e6ffe6'), use_container_width=True)
        col3.plotly_chart(create_indicator(avg_opp, '📊 Avg. Opportunity Size', '#fff3e6'), use_container_width=True)

    # Charts
    st.header("Sales & Opportunities")
    line_chart = create_line_chart(filtered_sales)
    if line_chart:
        st.plotly_chart(line_chart, use_container_width=True)
    
    cumulative_chart = create_cumulative_chart(filtered_sales)
    if cumulative_chart:
        st.plotly_chart(cumulative_chart, use_container_width=True)

    st.header("Marketing and Opportunity Analysis")
    col5, col6 = st.columns(2)
    donut_chart = create_donut_chart(filtered_sales)
    bar_chart = create_bar_chart(opp_df)
    if donut_chart:
        col5.plotly_chart(donut_chart, use_container_width=True)
    if bar_chart:
        col6.plotly_chart(bar_chart, use_container_width=True)

    # size_chart = create_size_chart(opp_df)
    # if size_chart:
    #     st.plotly_chart(size_chart, use_container_width=True)
    
    st.header("Sales Per Country")
    sales_country_chart = create_sales_by_country_chart(filtered_sales)
    if sales_country_chart:
        st.plotly_chart(sales_country_chart, use_container_width=True)

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
                response = requests.post("http://localhost:8000/predict", json=payload)
                response.raise_for_status()
                forecast_data = response.json()
                forecast_df = pd.DataFrame(forecast_data)

                # Display
                st.subheader(f"Forecasted Sales for {country} ({freq}, next {periods})")
                fig = px.line(forecast_df, x="Date", y="Predicted Sales", title="📈 Forecast from Prophet")
                st.plotly_chart(fig, use_container_width=True)

            except requests.exceptions.RequestException as e:
                st.error(f"Failed to get forecast: {e}")



if __name__ == "__main__":
    main()
