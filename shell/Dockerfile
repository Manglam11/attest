FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/
WORKDIR /code
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt
COPY . .
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "220", "--reload"]