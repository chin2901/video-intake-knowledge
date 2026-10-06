FROM python:3.11-slim-bookworm

# Instalar ffmpeg y curl minimo
RUN apt-get update &&     apt-get install -y --no-install-recommends ffmpeg curl &&     rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
RUN mkdir -p /app/storage

EXPOSE 8090

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
