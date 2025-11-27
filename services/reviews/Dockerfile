FROM python:3.12-slim
WORKDIR /reviews

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Listen on the port mapped in docker-compose (8004)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004", "--reload"]