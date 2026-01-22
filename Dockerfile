#############
### Build ###
#############
FROM alpine:3.13 as build

# Set src dirs
ENV APP_DIR=/srv/app
ENV PIP_SRC=${APP_DIR}
ENV JOB_CONFIG ${APP_DIR}/datapusher_settings.py

WORKDIR ${APP_DIR}

# Packages to build datapusher
RUN apk add --no-cache \
    python3 \
    # Temporary packages to build DataPusher requirements
    && apk add --no-cache --virtual .build-deps \
    py3-pip \
    py3-wheel \
    libffi-dev \
    libressl-dev \
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
RUN pip3 wheel --wheel-dir=/wheels .
RUN pip3 wheel --wheel-dir=/wheels -r requirements.txt

# Copy requirements.txt to /wheels
RUN cp requirements.txt /wheels/requirements.txt

RUN apk del .build-deps && \
    rm -rf ${APP_DIR}/src

############
### MAIN ###
############
FROM alpine:3.13 as main

ENV APP_DIR=/usr/lib/ckan/datapusher
ENV WSGI_FILE ${APP_DIR}/src/datapusher/deployment/datapusher.wsgi
ENV WSGI_CONFIG ${APP_DIR}/datapusher-uwsgi.ini

RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
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

RUN pip3 install --no-index --find-links=/wheels datapusher && \
    pip3 install --no-index --find-links=/wheels -r /wheels/requirements.txt && \
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

# Create a local user and group to run the app
RUN addgroup -g 92 -S www-data && \
    adduser -u 92 -h /srv/app -H -D -S -G www-data www-data

EXPOSE 8800

USER www-data

CMD ["sh", "-c", \
    "uwsgi --plugins=http,python --http=0.0.0.0:8800 --socket=/tmp/uwsgi.sock --ini=`echo ${APP_DIR}`/datapusher-uwsgi.ini --wsgi-file=`echo ${APP_DIR}`/datapusher.wsgi"]
