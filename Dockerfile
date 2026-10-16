FROM python:3.11-alpine

RUN apk update && apk add --no-cache ffmpeg git build-base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["python", "app.py"]
