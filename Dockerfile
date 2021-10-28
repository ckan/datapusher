FROM ubuntu:14.04
MAINTAINER  Kyle Falconer "kyle.falconer@vta.org"

#install requirements for the DataPusher
RUN apt-get update && apt-get install -y \
  libxslt1-dev \
  libxml2-dev \
  git \
  libpq-dev \
  python-dev \
  python-setuptools \
  build-essential \
  apache2 \
  libapache2-mod-wsgi

RUN easy_install pip
RUN pip install --upgrade pip
RUN pip install --upgrade virtualenv
RUN pip install virtualenvwrapper

RUN /bin/bash -c "source /usr/local/bin/virtualenvwrapper.sh"

#create a virtualenv for datapusher
RUN virtualenv /usr/lib/ckan/datapusher

#create a source directory and switch to it
RUN mkdir /usr/lib/ckan/datapusher/src
WORKDIR /usr/lib/ckan/datapusher/src

#clone the source (always target the stable branch)
RUN git clone -b stable https://github.com/ckan/datapusher.git

#install the DataPusher and its requirements
WORKDIR /usr/lib/ckan/datapusher/src/datapusher
RUN /usr/lib/ckan/datapusher/bin/pip install -r requirements.txt
RUN /usr/lib/ckan/datapusher/bin/python setup.py develop

#copy the standard Apache config file
# (use deployment/datapusher.apache2-4.conf if you are running under Apache 2.4)
RUN cp deployment/datapusher.apache2-4.conf /etc/apache2/sites-available/datapusher.conf

RUN mkdir -p /etc/ckan

#copy the standard DataPusher wsgi file
#(see note below if you are not using the default CKAN install location)
RUN cp deployment/datapusher.wsgi /etc/ckan/

#copy the standard DataPusher settings.
RUN cp deployment/datapusher_settings.py /etc/ckan/

#open up port 8800 on Apache where the DataPusher accepts connections.
#make sure you only run these 2 functions once otherwise you will need
#to manually edit /etc/apache2/ports.conf.
RUN sh -c 'echo "NameVirtualHost *:8800" >> /etc/apache2/ports.conf'
RUN sh -c 'echo "Listen 8800" >> /etc/apache2/ports.conf'

#enable DataPusher Apache site
RUN a2ensite datapusher

ADD deployment/apache_fg.sh /
RUN chmod +x /apache_fg.sh
CMD /apache_fg.sh