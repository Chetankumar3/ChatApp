FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /ping

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 50050

CMD ["python","-m", "backend.main_service.main", "--host", "0.0.0.0", "--http_port", "8000", "--grpc_port", "50050"]