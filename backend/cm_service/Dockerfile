FROM python:3.11-slim

RUN apt-get update && apt-get install -y dos2unix && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/cm_service
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# dos2unix is for converting CRLF to LF
RUN dos2unix /app/cm_service/entrypoint.sh && chmod +x /app/cm_service/entrypoint.sh

WORKDIR /app

EXPOSE 8001 50051

ENTRYPOINT ["/app/cm_service/entrypoint.sh"]
CMD ["python","-m", "cm_service.main", "--host", "0.0.0.0", "--http_port", "8001", "--grpc_port", "50051"]