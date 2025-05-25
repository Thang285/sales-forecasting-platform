from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal
import pandas as pd
import joblib
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from statsmodels.tsa.arima.model import ARIMAResults
from sqlalchemy import text
import os
import logging

# --- CONFIGURATION ---
DB_HOST = os.environ.get('DB_HOST', 'your-app-db.default.svc.cluster.local')
DB_NAME = os.environ.get('DB_NAME', 'your_database')
DB_USER = os.environ.get('DB_USER', 'your_user')
DB_PASS = os.environ.get('DB_PASSWORD', 'your_password')
DB_PORT = 5432
TABLE_NAME = "online_retail_data"
MODEL_DIR = "./models"

# --- ASYNC DATABASE SETUP ---
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# --- FASTAPI INIT ---
app = FastAPI()

# --- INPUT SCHEMA ---
class ForecastRequest(BaseModel):
    country: str
    freq: Literal["D", "M", "Y"] = "D"
    periods: int = 30

# --- DATA FETCHING ---
async def fetch_data(session: AsyncSession, country: str, freq: str) -> pd.DataFrame:
    query = text('''
        SELECT "InvoiceDate", "Quantity", "UnitPrice"
        FROM online_retail_data
        WHERE "Quantity" > 0 AND "UnitPrice" > 0 AND "Country" = :country
    ''')
    result = await session.execute(query, {"country": country})
    rows = result.fetchall()
    df = pd.DataFrame(rows, columns=result.keys())

    if df.empty or "InvoiceDate" not in df.columns:
        raise ValueError("No data found or missing 'InvoiceDate' column.")

    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['SaleAmount'] = df['Quantity'] * df['UnitPrice']

    grouped = df.groupby(pd.Grouper(key="InvoiceDate", freq=freq))['SaleAmount'].sum().reset_index()
    grouped.columns = ['ds', 'y']
    return grouped.dropna()

# --- HEALTH CHECK ---
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# --- PREDICTION ROUTE ---
@app.post("/predict")
async def predict(req: ForecastRequest):
    model_path = os.path.join(MODEL_DIR, "arima.pkl")

    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="ARIMA model not found.")

    try:
        model: ARIMAResults = joblib.load(model_path)

        async with AsyncSessionLocal() as session:
            df = await fetch_data(session, country=req.country, freq=req.freq)

        df = df.sort_values("ds")
        df.set_index("ds", inplace=True)

        forecast_result = model.forecast(steps=req.periods)

        # Map input freq to pandas-compatible frequency strings
        freq_map = {"D": "D", "M": "MS", "Y": "YS"}
        pandas_freq = freq_map.get(req.freq, "D")

        forecast = pd.DataFrame({
            "Date": pd.date_range(start=df.index[-1] + pd.Timedelta(days=1), periods=req.periods, freq=pandas_freq),
            "Predicted Sales": forecast_result
        })

        return forecast.to_dict(orient="records")

    except Exception as e:
        logging.exception("❌ Exception during ARIMA prediction")
        raise HTTPException(status_code=500, detail=str(e))
