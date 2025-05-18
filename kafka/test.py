import psycopg2
import os

DB_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
DB_NAME = os.environ.get('POSTGRES_DB', 'your_database')
DB_USER = os.environ.get('POSTGRES_USER', 'your_user')
DB_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'your_password')

conn = psycopg2.connect(
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

cur = conn.cursor()
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'online_retail_data';
""")

columns = cur.fetchall()
for col in columns:
    print(f"{col[0]} ({col[1]})")

cur.close()
conn.close()
