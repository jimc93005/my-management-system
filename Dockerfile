# 1. Use the official Python 3.12.3 lightweight image
FROM python:3.12.3-slim

# 2. Set environment variables to keep Python behavior predictable
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Create and set the working directory inside the container
WORKDIR /app
# 4. Install system dependencies (Crucial for PostgreSQL, pycairo, and WeasyPrint)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    pkg-config \
    libcairo2-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*
# 5. Copy your requirements file and install Python packages
COPY requirements.txt /app/
# Dockerfile

RUN pip install --default-timeout=1000 --upgrade pip && pip install --default-timeout=1000 -r requirements.txt

# 6. Copy the rest of your project files into the container
COPY . /app/

# 7. Expose the port your app will run on
EXPOSE 8000

# 8. The command that starts your application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]