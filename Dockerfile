FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

# Set work directory
WORKDIR /app

# Install Python dependencies (Playwright package may be newer than the image tag)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && PLAYWRIGHT_BROWSERS_PATH=0 python -m playwright install --with-deps chromium

# Copy the rest of the application code
COPY . .

# Browsers live inside the Playwright package (see PLAYWRIGHT_BROWSERS_PATH=0 above)
ENV PLAYWRIGHT_BROWSERS_PATH=0

# Run Alembic migrations (if any) and start the Uvicorn server
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 10000
