import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine
import joblib
import os

# --- CONFIGURE DATABASE ---
DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
DB_PORT = "5432"
DB_NAME = os.environ.get('POSTGRES_DB', 'your_database')
DB_USER = os.environ.get('POSTGRES_USER', 'your_user')
DB_PASS  = os.environ.get('POSTGRES_PASSWORD', 'your_password')
TABLE_NAME = "online_retail_data"

# --- CONNECT TO DATABASE ---
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
query = f'''
    SELECT "InvoiceDate", "Quantity", "UnitPrice", "Country"
    FROM {TABLE_NAME}
    WHERE "Quantity" > 0 AND "UnitPrice" > 0
'''
df = pd.read_sql_query(query, engine)

# --- CLEAN & TRANSFORM ---
df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
df['SaleAmount'] = df['Quantity'] * df['UnitPrice']

# Example: train for a specific country, e.g., United Kingdom
country = "United Kingdom"
country_df = df[df['Country'] == country]

# Aggregate by day
daily = country_df.groupby(pd.Grouper(key='InvoiceDate', freq='D'))['SaleAmount'].sum().reset_index()
daily.columns = ['ds', 'y']

# Drop NaNs (Prophet requirement)
daily.dropna(inplace=True)

# --- TRAIN MODEL ---
model = Prophet()
model.fit(daily)

# --- SAVE MODEL ---
os.makedirs("../models", exist_ok=True)
model_path = f"../models/prophet_model_{country.replace(' ', '_')}.pkl"
joblib.dump(model, model_path)

print(f"✅ Model for {country} trained and saved to {model_path}")
