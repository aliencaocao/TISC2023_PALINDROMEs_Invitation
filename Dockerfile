# Use the latest version of Ubuntu server as the base image
FROM ubuntu:latest

# Install required packages
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y unzip xvfb libxi6 libgconf-2-4 chromium-driver python3 python3-pip && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*


# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt and password_checker.py into the container
COPY requirements.txt .
COPY password_checker.py .

# Install Python dependencies from requirements.txt
RUN pip3 install -U -r requirements.txt

EXPOSE 7000

# Run the password_checker.py script
CMD ["python3", "password_checker.py"]
