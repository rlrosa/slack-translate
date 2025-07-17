# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# This is only required for the docker production image
RUN pip install --no-cache-dir gunicorn

# Expose the port your Flask app will run on
# Default for Gunicorn is 8000
EXPOSE 8000

# Define environment variable
ENV FLASK_APP=bot.py

# Set environment variables for Slack tokens (to be overridden in deployment)
ENV SLACK_BOT_TOKEN=""
ENV SLACK_APP_TOKEN=""

# Command to run the application using Gunicorn
# 'bot:app' assumes your Flask application instance is named 'app'
# and is located in a file named 'bot.py'.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "bot:app"]