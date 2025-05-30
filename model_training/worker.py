import os
import json
import asyncio
import logging
import pandas as pd
import joblib
import redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from statsmodels.tsa.arima.model import ARIMA
from datetime import datetime

# Database configuration from environment variables
DB_HOST = os.environ.get('DB_HOST', 'your-app-db.default.svc.cluster.local')
DB_NAME = os.environ.get('DB_NAME', 'your_database')
DB_USER = os.environ.get('DB_USER', 'your_user')
DB_PASS = os.environ.get('DB_PASSWORD', 'your_password')
DB_PORT = 5432
MODEL_DIR = "/app/models"  # Mounted path inside container
MODEL_PATH = os.path.join(MODEL_DIR, "arima.pkl")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Redis client to connect to Redis service
redis_host = os.environ.get('REDIS_HOST', 'redis-service')  # Kubernetes service name for Redis
redis_port = int(os.environ.get('REDIS_PORT', 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

async def fetch_training_data(session: AsyncSession, country: str, freq: str) -> pd.DataFrame:
    query = text('''
        SELECT "InvoiceDate", "Quantity", "UnitPrice"
        FROM online_retail_data
        WHERE "Quantity" > 0 AND "UnitPrice" > 0 AND "Country" = :country
    ''')
    result = await session.execute(query, {"country": country})
    rows = result.fetchall()
    df = pd.DataFrame(rows, columns=result.keys())

    if df.empty:
        raise ValueError(f"No training data found for country: {country}")

    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['SaleAmount'] = df['Quantity'] * df['UnitPrice']

    grouped = df.groupby(pd.Grouper(key="InvoiceDate", freq=freq))['SaleAmount'].sum().reset_index()
    grouped.columns = ['ds', 'y']
    return grouped.dropna()

async def retrain_model(country: str, freq: str):
    logging.info(f"Starting retraining for country={country}, freq={freq}")
    async with AsyncSessionLocal() as session:
        df = await fetch_training_data(session, country, freq)

    df = df.sort_values("ds")
    df.set_index("ds", inplace=True)

    model = ARIMA(df['y'], order=(5,1,0))
    model_fit = model.fit()

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model_fit, MODEL_PATH)

    logging.info(f"Model retrained and saved at {MODEL_PATH} on {datetime.now()}")

async def worker_loop():
    logging.basicConfig(level=logging.INFO)
    logging.info("Worker started and listening for retrain jobs...")

    while True:
        try:
            # Block until a retrain job is available in Redis list 'retrain_jobs' with 5s timeout
            job = redis_client.brpop("retrain_jobs", timeout=5)
            if job:
                _, job_data = job
                params = json.loads(job_data)
                country = params.get("country", "United Kingdom")
                freq = params.get("freq", "D")
                logging.info(f"Received retrain job: country={country}, freq={freq}")

                await retrain_model(country, freq)
                logging.info("Retrain job completed successfully.")
            else:
                # No job received within timeout, sleep briefly before retrying
                await asyncio.sleep(1)
        except Exception as e:
            logging.error(f"Error processing retrain job: {e}")
            await asyncio.sleep(5)  # Wait before retry on error

if __name__ == "__main__":
    asyncio.run(worker_loop())
