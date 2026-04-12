FROM python:3.11-slim

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user
WORKDIR /app

# Install dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY --chown=user . .

# Switch to the "user" user
USER user

# Expose the port Hugging Face Spaces expects
EXPOSE 7860

# Hugging Face Spaces expects the app to be on port 7860
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
