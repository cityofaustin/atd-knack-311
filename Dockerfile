FROM python:3.11-slim

# Copy our own application
WORKDIR /app
COPY . /app/atd-knack-311

RUN chmod -R 755 /app/*

# # Proceed to install the requirements...do
RUN cd /app/atd-knack-311 && apt-get update && \
    pip install -r requirements.txt
