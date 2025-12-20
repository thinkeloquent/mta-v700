FROM python:3.11-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy package files
COPY packages_py/db_connection_postgres /packages/db_connection_postgres
COPY examples/fastapi-example/pyproject.toml examples/fastapi-example/main.py ./

# Update pyproject.toml for Docker context
RUN sed -i 's|path = "../../packages_py/db_connection_postgres"|path = "/packages/db_connection_postgres"|' pyproject.toml

# Install dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
