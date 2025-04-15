FROM python:3.13.3-bookworm
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV PATH="/scripts:${PATH}"

COPY ./requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y gcc libc-dev 
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt
RUN playwright install chromium
RUN mkdir /app 

COPY . /app
WORKDIR /app


RUN python3 manage.py makemigrations 