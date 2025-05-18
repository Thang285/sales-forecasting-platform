import random
import json
import time
from kafka import KafkaProducer
from datetime import datetime, timedelta

# Kafka producer setup
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',  # Adjust if using cloud Kafka
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Simulated data generator
start_time = datetime.strptime("09/12/2011 00:00", "%d/%m/%Y %H:%M")
stock_codes = [str(random.randint(10000, 99999)) for _ in range(50)]
descriptions = [
    "WHITE HANGING HEART T-LIGHT HOLDER", "WHITE METAL LANTERN", "CREAM CUPID HEARTS COAT HANGER",
    "RED POLKA DOT BOWL", "GLASS STAR FROSTED T-LIGHT HOLDER", None
]
customers = [str(random.randint(12345, 54321)) for _ in range(10)]
countries = ["United Kingdom", "Germany", "France", "Australia", "Spain", "Norway"]

for i in range(100):  # Simulate 100 entries
    invoice_time = start_time + timedelta(minutes=i * 3)  # Every 3 minutes
    data = {
        "InvoiceNo": 600000 + i,
        "StockCode": random.choice(stock_codes),
        "Description": random.choice(descriptions),
        "Quantity": random.randint(1, 10),
        "InvoiceDate": invoice_time.strftime("%d/%m/%Y %H:%M"),
        "UnitPrice": round(random.uniform(1.0, 20.0), 2),
        "CustomerID": random.choice(customers),
        "Country": random.choice(countries)
    }
    
    # Send data to Kafka topic "sales"
    producer.send('sales', value=data)
    print(f"Produced: {data}")
    time.sleep(1)  # simulate streaming
