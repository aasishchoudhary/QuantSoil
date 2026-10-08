FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY packages ./packages
COPY services ./services
COPY schemas ./schemas
COPY migrations ./migrations
COPY db ./db
RUN python -m pip install --no-cache-dir --upgrade pip && python -m pip install --no-cache-dir .
USER 10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "services.runtime.service:app", "--host", "0.0.0.0", "--port", "8080"]
