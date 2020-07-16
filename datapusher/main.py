import os
import six
import ckanserviceprovider.web as web

from datapusher import jobs

# check whether jobs have been imported properly
assert(jobs.push_to_datastore)


def serve():
    web.init()
    web.app.run(web.app.config.get('HOST'), web.app.config.get('PORT'))


def serve_test():
    web.init()
    return web.app.test_client()


def main():
    import argparse

    argparser = argparse.ArgumentParser(
        description='Service that allows automatic migration of data to the CKAN DataStore',
        epilog='''"He reached out and pressed an invitingly large red button on a nearby panel.
                The panel lit up with the words Please do not press this button again."''')
    if six.PY3:
        argparser.add_argument('config', metavar='CONFIG', type=argparse.FileType('r'),
                            help='configuration file')
    if six.PY2:
        argparser.add_argument('config', metavar='CONFIG', type=file,
                            help='configuration file')
    args = argparser.parse_args()

    os.environ['JOB_CONFIG'] = os.path.abspath(args.config.name)
    serve()

if __name__ == '__main__':
    main()
