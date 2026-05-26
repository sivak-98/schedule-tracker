FROM python:3.12
# Set the working directory
WORKDIR /schedule-tracker
# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
# Copy the application code and the entrypoint script
COPY . .
# Expose the port
EXPOSE 5000

# Set the entrypoint to the entrypoint script
CMD ["sh", "-c", "python app.py"]
