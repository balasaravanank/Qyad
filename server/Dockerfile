FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app/server
COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --gid 10001 qyad \
    && useradd --uid 10001 --gid qyad --no-create-home --shell /usr/sbin/nologin qyad \
    && mkdir -p /data/backups && chown -R qyad:qyad /data
COPY --chown=qyad:qyad server/app ./app
COPY --chown=qyad:qyad server/scripts ./scripts
COPY --chown=qyad:qyad client/public /app/client/public
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD ["python", "-c", "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=4); assert r.status==200"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
