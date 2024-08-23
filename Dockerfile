FROM python:3-alpine
EXPOSE 5000

ENV TZ=Europe/Athens
ENV RUN_INSIDE_DOCKER=1
ENV PATH=$PATH:/messenger

RUN apk update
RUN apk upgrade
RUN mkdir /messenger-async
WORKDIR /messenger-async

COPY ./app /messenger-async/app
COPY ./databases /messenger-async/databases
COPY ./logger /messenger-async/logger
COPY ./models /messenger-async/models
COPY ./services /messenger-async/services
COPY ./utils /messenger-async/utils
COPY ./requirements.txt /messenger-async/requirements.txt
RUN pip3 install -r requirements.txt --break-system-packages