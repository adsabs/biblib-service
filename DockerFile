FROM python:3.8

WORKDIR /app

ENV UBUNTU_FRONTEND=noninteractive
USER root
RUN apt-get update && apt-get install -y postgresql

RUN python -m pip install --upgrade wheel pip
COPY requirements.txt /app
RUN pip install --no-cache-dir -U -r requirements.txt
COPY dev-requirements.txt /app
RUN pip install --no-cache-dir -U -r dev-requirements.txt

RUN useradd -ms /bin/bash ads
