FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi.py

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app \
    && chmod +x docker/entrypoint.sh \
    && mkdir -p /var/log/app \
    && chown appuser:appuser /var/log/app

USER appuser

# No curl in python:3.12-slim — use the stdlib instead of adding a package
# just for this.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz', timeout=3)" || exit 1

ENTRYPOINT ["docker/entrypoint.sh"]
# Bare `gunicorn` defaults to 1 worker — fine for nothing. Workers kept
# modest (not 2*CPU+1) since Postgres shares the same 1GB free-tier box
# in the demo deployment. No --access-logfile: the app already emits
# structured JSON per request (app/utils/request_logging.py); gunicorn's
# own access log would just duplicate it.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "30", "wsgi:app"]
