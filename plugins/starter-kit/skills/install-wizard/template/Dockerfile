# Pinned to the Python line the Cowork VM runs, so local and container match.
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    DATA_DIR=/data \
    DJANGO_SETTINGS_MODULE=project.settings.prod

WORKDIR /app

COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt

COPY . .

# SQLite needs to create -wal and -shm files, so the directory must be
# writable, not just the database file.
RUN useradd --create-home app && mkdir -p /data && chown -R app:app /app /data
USER app

EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
