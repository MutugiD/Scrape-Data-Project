# Use official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy setup and source code, then install the package
COPY setup.py ./
COPY src/ ./src/
RUN pip install --no-cache-dir .

# Copy any remaining files (e.g., main script, config)
COPY . .

# Default command to run the scraper
CMD ["python", "main.py"]
