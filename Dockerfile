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

# Copy python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bundle the python core packages inside the container image
COPY dummy2/ /app/dummy2/
COPY helpers/ /app/helpers/
