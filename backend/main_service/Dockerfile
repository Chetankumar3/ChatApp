FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/main_service
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
WORKDIR /app

EXPOSE 8000 50050

CMD ["python","-m", "main_service.main", "--host", "0.0.0.0", "--http_port", "8000", "--grpc_port", "50050"]