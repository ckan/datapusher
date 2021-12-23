FROM ubuntu:20.04

RUN apt-get update
RUN apt-get install -y python3-venv python3-dev python3-pip python3-wheel

#Create a virtualenv for datapusher
RUN python3 -m venv /usr/lib/ckan/datapusher

# Create a source directory and copy source files
RUN mkdir -p /usr/lib/ckan/datapusher/src/datapusher
ADD . /usr/lib/ckan/datapusher/src/datapusher

# Install the DataPusher and its requirements
RUN cd /usr/lib/ckan/datapusher/src/datapusher
RUN /usr/lib/ckan/datapusher/bin/pip install wheel
RUN /usr/lib/ckan/datapusher/bin/pip install -U 'chardet >= 3.0.2, < 4'
RUN /usr/lib/ckan/datapusher/bin/pip install requests

#RUN cd /usr/lib/ckan/datapusher/src/datapusher &&  \
#    /usr/lib/ckan/datapusher/bin/pip install -r requirements.txt && \
#    /usr/lib/ckan/datapusher/bin/python setup.py develop
WORKDIR /usr/lib/ckan/datapusher/src/datapusher
RUN /usr/lib/ckan/datapusher/bin/pip install -r requirements.txt
RUN /usr/lib/ckan/datapusher/bin/python setup.py develop

# Create a user to run the web service (if necessary)
RUN addgroup www-data ; exit 0
RUN adduser www-data www-data ; exit 0

# Install uWSGI
RUN /usr/lib/ckan/datapusher/bin/pip install uwsgi

# Replace 127.0.0.1 with 0.0.0.0 (to bind to all addresses)
RUN sed -i "s|127.0.0.1|0.0.0.0|g" /usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher-uwsgi.ini

# EXEC
CMD ["/usr/lib/ckan/datapusher/bin/uwsgi", "-i", "/usr/lib/ckan/datapusher/src/datapusher/deployment/datapusher-uwsgi.ini"]

EXPOSE 8800







