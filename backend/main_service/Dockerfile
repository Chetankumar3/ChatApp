FROM python:3.11-slim

RUN apt-get update && apt-get install -y dos2unix && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/main_service
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# FIX 1: Point dos2unix to the correct copied path
RUN dos2unix /app/main_service/entrypoint.sh && chmod +x /app/main_service/entrypoint.sh

WORKDIR /app
EXPOSE 8000 50050

# FIX 2: Point ENTRYPOINT to the correct copied path
ENTRYPOINT ["/app/main_service/entrypoint.sh"]
CMD ["python","-m", "main_service.main", "--host", "0.0.0.0", "--http_port", "8000", "--grpc_port", "50050"]