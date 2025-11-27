FROM python:3.12-slim
WORKDIR /rooms

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
 # Listen on the port mapped in docker-compose (8002)
 CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]