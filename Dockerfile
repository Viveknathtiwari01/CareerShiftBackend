FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Run Alembic migrations (if any) and start the Uvicorn server
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 10000
