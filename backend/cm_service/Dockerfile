FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /ping

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001 50051

CMD ["python","-m", "backend.cm_service.main", "--host", "0.0.0.0", "--http_port", "8001", "--grpc_port", "50051"]