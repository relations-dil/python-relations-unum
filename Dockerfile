FROM python:3

RUN mkdir -p /opt/service

WORKDIR /opt/service

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY setup.py .
COPY lib lib

ENV PYTHONPATH="/opt/service/lib"
