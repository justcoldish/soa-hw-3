FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
ENV PATH="/app/.venv/bin:$PATH"
COPY proto proto
RUN python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/flight.proto
ARG SERVICE
COPY $SERVICE .
CMD ["python", "main.py"]
