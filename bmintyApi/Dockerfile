# Dockerfile
FROM python:3.11

# Set working directory
WORKDIR /bmintyApi

# Install system packages (bedtools) and clean up apt caches to keep image small
RUN apt-get update \
	&& apt-get install -y --no-install-recommends sqlite3 less \
	&& rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project files
COPY . .

# Expose Django port (default 8000, configurable via BACKEND_PORT env var)
EXPOSE ${BACKEND_PORT:-8000}

# Use startup script that handles both fresh and imported databases
CMD ["sh", "./startup.sh"]
