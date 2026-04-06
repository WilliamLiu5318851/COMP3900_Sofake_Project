FROM python:3.12-slim

WORKDIR /app

# Install test dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project so all modules are importable
COPY .. .

# Default: run all tests with verbose output
CMD ["pytest", "tests/", "-v", "--tb=short"]
