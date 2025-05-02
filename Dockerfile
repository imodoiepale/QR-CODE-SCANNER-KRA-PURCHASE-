FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install lxml parser which is required for BeautifulSoup
RUN apt-get update && apt-get install -y libxml2-dev libxslt-dev gcc && \
    pip install lxml && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Command to run the application
# Railway.app sets the PORT environment variable automatically
CMD uvicorn main:app --host 0.0.0.0 --port 8000