FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DBT_SEND_ANONYMOUS_USAGE_STATS=false
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src src
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 pipeline
COPY dbt dbt
RUN mkdir -p data && chown -R pipeline:pipeline /app
USER pipeline
ENTRYPOINT ["macro"]
