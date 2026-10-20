# MT5 Linux Data Bridge Container
# Kết nối MetaTrader 5 Demo MetaQuotes qua mt5linux (Wine / RPyC) hoặc Windows native
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 5001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5001"]