FROM python:3.7-slim-stretch

MAINTAINER Alexandre Abadie <alexandre.abadie@inria.fr>

RUN apt-get update && apt-get install -y git && apt-get autoremove && apt-get autoclean
RUN pip3 install git+https://github.com/pyaiot/pyaiot.git

RUN aiot-generate-keys
