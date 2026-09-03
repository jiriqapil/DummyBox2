FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system utilities needed for detached loops (screen) and C-libraries for basemap/netCDF4
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    screen \
    libgeos-dev \
    libnetcdf-dev \
    libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ALL repository files into the image (launchers, demo, helpers, dummy2, run.py, etc.)
COPY . /app

# Set default execution command
CMD ["python3", "run.py"]
