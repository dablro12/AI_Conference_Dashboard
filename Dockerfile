FROM python:3.10.8-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
EXPOSE 5000

RUN apt update && apt install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app/

# requirements.txt를 먼저 복사하고 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 나머지 파일들 복사
COPY . .

CMD ["python", "app.py"]