FROM python:3.8

WORKDIR /app

ENV UBUNTU_FRONTEND=noninteractive
USER root
RUN apt-get update && apt-get install -y postgresql

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt
COPY dev-requirements.txt /app
RUN pip install --no-cache-dir -r dev-requirements.txt

RUN useradd -ms /bin/bash ads
