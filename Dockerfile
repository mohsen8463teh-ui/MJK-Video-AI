FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000 \
    MJK_STORAGE_ROOT=/app/storage \
    PIPER_DATA_DIR=/opt/piper/voices \
    PIPER_MODEL_FA=fa_IR-amir-medium \
    PIPER_MODEL_EN=en_US-lessac-medium

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt piper-tts \
    && mkdir -p /opt/piper/voices \
    && python -m piper.download_voices \
       --data-dir /opt/piper/voices \
       fa_IR-amir-medium \
       en_US-lessac-medium

COPY backend/ /app/

RUN mkdir -p /app/storage/projects

EXPOSE 5000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 3600 main:app"]
