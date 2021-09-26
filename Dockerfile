#############
### Build ###
#############
FROM python:3-alpine as build

# Set src dirs
ENV SRC_DIR=/srv/app/src
ENV PIP_SRC=${SRC_DIR}

WORKDIR ${SRC_DIR}

# Packages to build datapusher
RUN apk add --no-cache \
    curl \
    g++ \
    autoconf \
    automake \
    libtool \
    git \
    musl-dev \
    python3-dev \
    pcre-dev \
    libxml2-dev \
    libxslt-dev

# Create the src directory
RUN mkdir -p ${SRC_DIR}

# Copy datapusher to SRC_DIR
COPY ./README.md ${SRC_DIR}/README.md
COPY ./setup.py ${SRC_DIR}/setup.py
COPY ./requirements.txt ${SRC_DIR}/requirements.txt
COPY ./datapusher ${SRC_DIR}/datapusher

# Fetch and build datapusher and requirements
RUN pip wheel --wheel-dir=/wheels .
RUN pip wheel --wheel-dir=/wheels -r requirements.txt

# Copy requirements.txt to /wheels
RUN cp requirements.txt /wheels/requirements.txt

# Get uwsgi
RUN pip wheel --wheel-dir=/wheels uwsgi==2.0.19.1


############
### MAIN ###
############
FROM python:3-alpine as main

LABEL maintainer="Keitaro Inc <info@keitaro.com>"

ENV APP_DIR=/usr/lib/ckan/datapusher
ENV WSGI_FILE ${APP_DIR}/src/datapusher/deployment/datapusher.wsgi
ENV WSGI_CONFIG ${APP_DIR}/datapusher-uwsgi.ini

COPY ./deployment/datapusher.wsgi ${WSGI_FILE}
COPY ./deployment/datapusher-uwsgi.ini ${WSGI_CONFIG}

WORKDIR ${APP_DIR}

RUN apk add --no-cache \
        curl \
        pcre \
        libmagic \
        libxslt \
        libxml2

# Get artifacts from build stages
COPY --from=build /wheels /wheels

# Create a local user and group to run the app
RUN addgroup -g 92 -S www-data && \
    adduser -u 92 -h ${APP_DIR} -H -D -S -G www-data www-data && \
    # Setup a virtualenv
    python3 -m venv ${APP_DIR} && \
    ln -s /usr/lib/ckan/datapusher/bin/pip /usr/bin/pip && \
    # Install uwsgi
    pip install --no-index --find-links=/wheels uwsgi && \
    # Install datapusher
    pip install --no-index --find-links=/wheels datapusher && \
    pip install --no-index --find-links=/wheels -r /wheels/requirements.txt && \
    # Set timezone
    echo "UTC" >  /etc/timezone && \
    # Change uwsgi http worker to listen on all interfaces
    sed 's/127.0.0.1/0.0.0.0/g' -i ${APP_DIR}/datapusher-uwsgi.ini && \
    # Change ownership to app user
    chown -R www-data:www-data ${APP_DIR} && \
    # Remove wheels
    rm -rf /wheels

EXPOSE 8800

USER www-data

CMD $APP_DIR/bin/uwsgi -i $WSGI_CONFIG