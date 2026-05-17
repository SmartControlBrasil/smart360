FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system smart360 && useradd --system --gid smart360 --home-dir ${APP_HOME} smart360

COPY requirements ${APP_HOME}/requirements
RUN pip install --upgrade pip && pip install -r requirements/dev.txt

COPY deployment/scripts ${APP_HOME}/deployment/scripts
RUN chmod +x ${APP_HOME}/deployment/scripts/*.sh

COPY . ${APP_HOME}
RUN chmod +x ${APP_HOME}/scripts/*.sh \
    && mkdir -p ${APP_HOME}/media ${APP_HOME}/staticfiles \
    && chown -R smart360:smart360 ${APP_HOME}

USER smart360

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["/app/deployment/scripts/start-web.sh"]
