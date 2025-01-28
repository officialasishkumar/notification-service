FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY notification_service/requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY notification_service/ .

EXPOSE 8002

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]
