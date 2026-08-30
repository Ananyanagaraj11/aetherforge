FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt pyproject.toml README.md ./
COPY src ./src
COPY dashboard ./dashboard
COPY data ./data
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir -e .
ENV PYTHONPATH=src
EXPOSE 8080
CMD ["sh", "-c", "uvicorn aetherforge.api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
