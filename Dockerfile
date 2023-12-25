FROM python:3.8-slim

WORKDIR /app

COPY app.py .
COPY requirements.txt .
COPY db.sqlite .
COPY /templates .
COPY /instance .
COPY /__pycache__ .


RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "app.py", "tail", "-f", "/dev/null"]
