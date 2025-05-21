FROM python :3.9-slim

WORKDIR /app


COPY data_engineering/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY data_engineering/data_preprocessing.py .

CMD ["python", "data_preprocessing.py"]

