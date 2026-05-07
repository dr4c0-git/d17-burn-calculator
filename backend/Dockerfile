# Minimal Python image for the FastAPI backend.
FROM python:3.11-slim

WORKDIR /app

# System deps (none beyond what python:3.11-slim already ships).

# Python deps first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY main.py state.py solana_rpc.py ./

# Fly.io routes external traffic to whatever port the app listens on,
# defaulting to 8080 unless overridden in fly.toml.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
