Development installation
========================

Install the required packages::

    sudo apt-get install python-dev python-virtualenv build-essential libxslt1-dev libxml2-dev zlib1g-dev git libffi-dev

Get the code::

    git clone https://github.com/ckan/datapusher
    cd datapusher

Install the dependencies::

    pip install -r requirements.txt
    pip install -e .

Run the DataPusher::

    python datapusher/main.py deployment/datapusher_settings.py

By default DataPusher should be running at the following port:

    http://localhost:8800/

If you need to change the host or port, copy
`deployment/datapusher_settings.py` to
`deployment/datapusher_local_settings.py` and modify the file.
