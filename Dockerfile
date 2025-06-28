# Use official Node.js runtime as base image with Python support
FROM node:18-bullseye

# Install Python 3 and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python command
RUN ln -s /usr/bin/python3 /usr/bin/python

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install Node.js dependencies
RUN npm install

# Copy Python requirements file
COPY requirements.txt ./

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY aws_discovery_2_neo4j.py ./
COPY server.js ./
COPY LICENSE.md ./
COPY README.md ./

# Make the Node.js script executable
RUN chmod +x server.js

# Create directories for output
RUN mkdir -p /app/output /app/results

# Expose port for web interface
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Use the existing node user (UID 1000) instead of creating a new one
RUN chown -R node:node /app
USER node

# Default command
CMD ["npm", "start"]