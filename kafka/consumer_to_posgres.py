import json
import psycopg2
from kafka import KafkaConsumer
from psycopg2.extras import execute_values
import os
from datetime import datetime

# PostgreSQL connection settings
DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
DB_NAME = os.environ.get('POSTGRES_DB', 'your_database')
DB_USER = os.environ.get('POSTGRES_USER', 'your_user')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'your_password')

conn = psycopg2.connect(
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
)
cur = conn.cursor()

# Kafka consumer setup
consumer = KafkaConsumer(
    'sales',
    bootstrap_servers='localhost:9092',
    group_id='sales-consumer-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True
)

# Buffer for batch inserts
buffer = []
buffer_size = 10

def cast_row(d):
    """Ensure the values match the expected PostgreSQL types."""
    return (
        str(d.get('InvoiceNo')),
        str(d.get('StockCode')),
        d.get('Description'),  # None is OK for TEXT
        float(d.get('Quantity', 0)),
        datetime.strptime(d['InvoiceDate'], "%d/%m/%Y %H:%M"),
        float(d.get('UnitPrice', 0.0)),
        float(d.get('CustomerID', 0)),  # numeric in DB
        d.get('Country')
    )

def flush_to_postgres(batch):
    if not batch:
        return
    query = """
        INSERT INTO online_retail_data (
    "InvoiceNo", "StockCode", "Description", "Quantity",
    "InvoiceDate", "UnitPrice", "CustomerID", "Country"
    )
        VALUES %s
    """
    values = [cast_row(d) for d in batch]
    for row in values:
        print("🔄 Inserting row:", row)

    execute_values(cur, query, values)
    conn.commit()
    print(f"✅ Inserted {len(values)} rows into stream_data.\n")

# Start consuming
try:
    for msg in consumer:
        buffer.append(msg.value)
        if len(buffer) >= buffer_size:
            flush_to_postgres(buffer)
            buffer = []
except KeyboardInterrupt:
    print("⛔ Stopped by user.")
finally:
    flush_to_postgres(buffer)
    cur.close()
    conn.close()
