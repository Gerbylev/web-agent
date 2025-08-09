FROM mcr.microsoft.com/playwright/python:v1.54.0

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

COPY src .

CMD ["uv", "run", "--no-dev", "main.py"]
