FROM python:3.12.8

# Set the working directory in the container to /app
WORKDIR /app

ENV UBUNTU_FRONTEND=noninteractive
USER root
RUN apt-get update && apt-get install -y postgresql

# Add the current directory contents into the container at /app
ADD . /app

# setuptools>=58 breaks support for use_2to3 that is used by ConcurrentLogHandler in adsmutils
RUN pip install "pip==24" "setuptools>=62.0.0,<70.0.0"

# Install dependencies
RUN pip install .

RUN useradd -ms /bin/bash ads

EXPOSE 5000
