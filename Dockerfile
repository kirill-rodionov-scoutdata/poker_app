FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
RUN pip install .

COPY . /app

CMD ["python", "main.py"]
