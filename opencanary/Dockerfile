FROM python:3.11-slim

# Paquetes mínimos + zona horaria coherente
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tzdata && \
    rm -rf /var/lib/apt/lists/*

# OpenCanary desde PyPI (soporta plugins básicos)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir opencanary[plugins]

# Config y entrypoint
WORKDIR /opt/opencanary
COPY opencanary.conf.tmpl.json /opt/opencanary/opencanary.conf.tmpl.json
COPY entrypoint.py /opt/opencanary/entrypoint.py

ENV PYTHONUNBUFFERED=1
CMD ["python", "/opt/opencanary/entrypoint.py"]
