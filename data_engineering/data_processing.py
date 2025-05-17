import pandas as pd
import subprocess
import os
import psycopg2
from psycopg2 import sql
import numpy as np
import csv
from io import StringIO

def load_data_to_postgres(df, table_name, host, database, user, password):
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()

        # Create table if it doesn't exist
        columns_with_types = []
        for col, dtype in zip(df.columns, df.dtypes):
            if col == 'InvoiceNo':
                pg_dtype = 'TEXT'
            elif col == 'StockCode':
                pg_dtype = 'TEXT'
            elif col == 'Description':
                pg_dtype = 'TEXT'
            elif col == 'Quantity':
                pg_dtype = 'INTEGER'
            elif col == 'InvoiceDate':
                pg_dtype = 'TIMESTAMP'
            elif col == 'UnitPrice':
                pg_dtype = 'NUMERIC'
            elif col == 'CustomerID':
                pg_dtype = 'NUMERIC'
            elif col == 'Country':
                pg_dtype = 'TEXT'
            columns_with_types.append(sql.Composed([sql.Identifier(col), sql.SQL(' ' + pg_dtype)]))

        create_table_query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                {}
            )
        """).format(
            sql.Identifier(table_name),
            sql.SQL(', ').join(columns_with_types)
        )

        cursor.execute(create_table_query)
        conn.commit()

        # Prepare CSV for COPY
        output = StringIO()
        columns = ['InvoiceNo', 'StockCode', 'Description', 'Quantity', 'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country']
        df = df[columns]
        df.to_csv(output, index=False, header=False, quoting=csv.QUOTE_ALL)
        output.seek(0)

        copy_sql = f"""
            COPY {table_name} FROM STDIN WITH CSV NULL '' 
        """
        cursor.copy_expert(copy_sql, output)
        conn.commit()
        print(f"✅ Data successfully loaded into table `{table_name}`")

    except Exception as e:
        print(f"❌ Error loading data into PostgreSQL: {e}")
        conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

def main():
    data_url = "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx"
    local_file_path = "/home/vietthangtk123/sales_forecasting_platform/data/processed/online_retail.xlsx"

    if not os.path.exists(local_file_path):
        try:
            subprocess.run(["wget", data_url, "-O", local_file_path], check=True)
            print(f"📥 Downloaded data to {local_file_path}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error downloading the dataset: {e}")
            exit()
    else:
        print(f"📁 File already exists at {local_file_path}")

    try:
        df = pd.read_excel(local_file_path)
        print("✅ Data loaded into Pandas DataFrame")
    except Exception as e:
        print(f"❌ Error loading the Excel file: {e}")
        exit()

    df.to_csv('online_retail_data.csv', index=False, encoding='utf-8')
    print("💾 Data saved to online_retail_data.csv")

    df_from_csv = pd.read_csv('online_retail_data.csv', encoding='utf-8')

    # === PREPROCESSING STARTS HERE ===
    print("🔧 Preprocessing data...")

    # Strip whitespace and convert blank strings ("") to NaN
    df_from_csv = df_from_csv.map(lambda x: np.nan if isinstance(x, str) and x.strip() == "" else x)

    # Drop rows with missing critical values
    df_from_csv.dropna(subset=['InvoiceNo', 'StockCode', 'InvoiceDate', 'Quantity', 'UnitPrice'], inplace=True)

    # Convert to correct types
    df_from_csv['InvoiceDate'] = pd.to_datetime(df_from_csv['InvoiceDate'], errors='coerce')
    df_from_csv.dropna(subset=['InvoiceDate'], inplace=True)

    df_from_csv['Quantity'] = pd.to_numeric(df_from_csv['Quantity'], errors='coerce').fillna(0).astype(int)
    df_from_csv['UnitPrice'] = pd.to_numeric(df_from_csv['UnitPrice'], errors='coerce').fillna(0.0)

    # Drop invalid values
    df_from_csv = df_from_csv[(df_from_csv['Quantity'] > 0) & (df_from_csv['UnitPrice'] > 0)]

    # Clean text fields, replace blanks with default
    df_from_csv['InvoiceNo'] = df_from_csv['InvoiceNo'].astype(str).str.strip().replace('', 'UNKNOWN')
    df_from_csv['StockCode'] = df_from_csv['StockCode'].astype(str).str.strip().replace('', 'UNKNOWN')
    df_from_csv['Description'] = df_from_csv['Description'].astype(str).str.strip().replace('', 'UNKNOWN')
    df_from_csv['Country'] = df_from_csv['Country'].astype(str).str.strip().replace('', 'UNKNOWN')

    # Convert CustomerID to float (Postgres NUMERIC)
    df_from_csv['CustomerID'] = pd.to_numeric(df_from_csv['CustomerID'], errors='coerce').fillna(0)

    print("✅ Preprocessing complete.")
    print(df_from_csv.info())
    print(df_from_csv.describe())
    # === PREPROCESSING ENDS HERE ===

    host = os.environ.get('POSTGRES_HOST', 'localhost')
    database = os.environ.get('POSTGRES_DB', 'your_database')
    user = os.environ.get('POSTGRES_USER', 'your_user')
    password = os.environ.get('POSTGRES_PASSWORD', 'your_password')

    load_data_to_postgres(df_from_csv, 'online_retail_data', host, database, user, password)

if __name__ == "__main__":
    main()
