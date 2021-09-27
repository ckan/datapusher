#############
### Build ###
#############
FROM python:3-alpine as build

# Set src dirs
ENV APP_DIR=/srv/app
ENV PIP_SRC=${APP_DIR}
ENV JOB_CONFIG ${APP_DIR}/datapusher_settings.py

WORKDIR ${APP_DIR}

# Packages to build datapusher
RUN apk add --no-cache \
    curl \
    libffi-dev \
    libressl-dev \
    # Temporary packages to build DataPusher requirements
    && apk add --no-cache --virtual .build-deps \
    gcc \
    git \
    musl-dev \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    libmagic \
    openssl-dev \
    cargo

# Create the src directory
RUN mkdir -p ${APP_DIR}/src
WORKDIR ${APP_DIR}/src

# Copy datapusher to APP_DIR
COPY ./README.md .
COPY ./setup.py .
COPY ./requirements.txt .
COPY ./datapusher ./datapusher

# Fetch and build datapusher and requirements
RUN pip wheel --wheel-dir=/wheels .
RUN pip wheel --wheel-dir=/wheels -r requirements.txt

# Copy requirements.txt to /wheels
RUN cp requirements.txt /wheels/requirements.txt

RUN apk del .build-deps && \
    rm -rf ${APP_DIR}/src

############
### MAIN ###
############
FROM python:3-alpine as main

LABEL maintainer="Keitaro Inc <info@keitaro.com>"

ENV APP_DIR=/usr/lib/ckan/datapusher
ENV WSGI_FILE ${APP_DIR}/src/datapusher/deployment/datapusher.wsgi
ENV WSGI_CONFIG ${APP_DIR}/datapusher-uwsgi.ini

RUN apk add --no-cache \
    curl \
    git \
    pcre \
    libmagic \
    libxslt \
    libxml2 \
    uwsgi \
    uwsgi-http \
    uwsgi-corerouter \
    uwsgi-python

WORKDIR ${APP_DIR}

COPY ./deployment/datapusher.wsgi .
COPY ./deployment/datapusher-uwsgi.ini .

# Get artifacts from build stages
COPY --from=build /wheels /wheels

RUN pip install --no-index --no-cache-dir --find-links=/wheels datapusher && \
    pip install --no-index --no-cache-dir --find-links=/wheels -r /wheels/requirements.txt && \
    # Set timezone
    echo "UTC" >  /etc/timezone && \
    # Change uwsgi http worker to listen on all interfaces
    sed 's/127.0.0.1/0.0.0.0/g' -i ${APP_DIR}/datapusher-uwsgi.ini && \
    # Remove default values in ini file
    sed -i '/http/d' ${APP_DIR}/datapusher-uwsgi.ini && \
    sed -i '/wsgi-file/d' ${APP_DIR}/datapusher-uwsgi.ini && \
    sed -i '/virtualenv/d' ${APP_DIR}/datapusher-uwsgi.ini && \
    # Remove wheels
    rm -rf /wheels

# Create a local user to run the app
RUN adduser -u 92 -h ${APP_DIR} -H -D -S -G www-data www-data

EXPOSE 8800

CMD ["sh", "-c", \
    "uwsgi --plugins=http,python --http=0.0.0.0:8800 --socket=/tmp/uwsgi.sock --ini=`echo ${APP_DIR}`/datapusher-uwsgi.ini --wsgi-file=`echo ${APP_DIR}`/datapusher.wsgi"]
