from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal
import pandas as pd
import joblib
from prophet import Prophet
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import logging
from sqlalchemy import text
# CONFIG
DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
DB_PORT = "5432"
DB_NAME = os.environ.get('POSTGRES_DB', 'your_database')
DB_USER = os.environ.get('POSTGRES_USER', 'your_user')
DB_PASS  = os.environ.get('POSTGRES_PASSWORD', 'your_password')
TABLE_NAME = "online_retail_data"

# ASYNC DB setup
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL, echo=False)
MODEL_DIR = f"../models"
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# FASTAPI
app = FastAPI()

# INPUT SCHEMA
class ForecastRequest(BaseModel):
    country: str
    freq: Literal["D", "M", "Y"] = "D"
    periods: int = 30

# HELPER: Fetch data from Postgres
async def fetch_data(session: AsyncSession, country: str, freq: str) -> pd.DataFrame:
    query = text('''
    SELECT "InvoiceDate", "Quantity", "UnitPrice"
    FROM online_retail_data
    WHERE "Quantity" > 0 AND "UnitPrice" > 0 AND "Country" = :country
    ''')
    result = await session.execute(query, {"country": country})
    rows = result.fetchall()
    df = pd.DataFrame(rows, columns=["InvoiceDate", "Quantity", "UnitPrice"])

    if df.empty:
        raise ValueError("No data found for this country.")

    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['SaleAmount'] = df['Quantity'] * df['UnitPrice']
    grouped = df.groupby(pd.Grouper(key="InvoiceDate", freq=freq))['SaleAmount'].sum().reset_index()
    grouped.columns = ['ds', 'y']
    return grouped.dropna()

# ROUTE
@app.post("/predict")
async def predict(req: ForecastRequest):
    model_path = os.path.join(MODEL_DIR, f"prophet_model_{req.country.replace(' ', '_')}.pkl")

    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="Model not found for this country.")

    try:
        model: Prophet = joblib.load(model_path)

        async with AsyncSessionLocal() as session:
            df = await fetch_data(session, country=req.country, freq=req.freq)

        future = model.make_future_dataframe(periods=req.periods, freq=req.freq)
        forecast = model.predict(future)[['ds', 'yhat']]
        forecast.rename(columns={'ds': 'Date', 'yhat': 'Predicted Sales'}, inplace=True)

        return forecast.tail(req.periods).to_dict(orient='records')

    except Exception as e:
        logging.exception("❌ Exception during prediction")
        raise HTTPException(status_code=500, detail=str(e))
