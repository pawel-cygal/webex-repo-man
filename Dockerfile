# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install system dependencies that might be needed by Python packages
# For example, build-essential for packages that compile from source
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
# --no-cache-dir: Disables the cache, which can reduce image size
# --trusted-host pypi.python.org: Can help in some network environments
RUN pip install --no-cache-dir --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Single worker is mandatory: APScheduler runs in-process so multiple
# workers would spawn duplicate schedulers and send messages N times.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "run:app"]
