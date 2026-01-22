FROM debian:buster

# Install required system packages
RUN apt-get -q -y update \
    && DEBIAN_FRONTEND=noninteractive apt-get -q -y upgrade \
    && apt-get -q -y install \
        python3-dev \
        python3-pip \
        python3-virtualenv \
        zlib1g-dev \
        libxml2-dev \
        libxslt1-dev \
        libffi-dev \
        # else error https://stackoverflow.com/questions/14547631/python-locale-error-unsupported-locale-setting
        locales \
        postgresql-client \
        build-essential \
        git \
        vim \
        wget \
    && apt-get -q clean \
    && rm -rf /var/lib/apt/lists/*


RUN python3 -m virtualenv --python=python3 /venv
ENV PATH="/venv/bin:$PATH"

# else error https://stackoverflow.com/questions/59633558/python-based-dockerfile-throws-locale-error-unsupported-locale-setting
ENV LC_ALL=C

# NO else https://github.com/ckan/datapusher/issues/132
#datapusher    |   File "/venv/src/datapusher/jobs.py", line 158, in check_response
#datapusher    |     request_url=request_url, response=response.text)
#datapusher    | datapusher.jobs.HTTPError: <unprintable HTTPError object>
#ENV DATAPUSHER_SSL_VERIFY=true

# Setup Datapusher
ADD . /venv/src/
RUN pip install -U pip && \
    cd /venv/src/ &&  \
    pip install --upgrade --no-cache-dir -r requirements.txt && \
    pip install --upgrade --no-cache-dir -r requirements-dev.txt && \
    #pip install -e .
    python setup.py develop
    
CMD [ "python", "/venv/src/datapusher/main.py", "/venv/src/deployment/datapusher_settings.py"]
