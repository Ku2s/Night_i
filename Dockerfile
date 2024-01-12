FROM python:3.8-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

RUN pip install gunicorn

CMD ["gunicorn", "-k", "geventwebsocket.gunicorn.workers.GeventWebSocketWorker", "app:app", "-b", "0.0.0.0:5000", "--forwarded-allow-ips", "*"]
