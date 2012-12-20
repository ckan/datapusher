import os

import ckanserviceprovider.web as web

import datastorer
import dataproxy

# check whether jobs have been imported properly
assert(datastorer.import_into_datastore)
assert(dataproxy.convert_resource)


def serve():
    web.configure()
    web.app.run()


def serve_test():
    web.configure()
    return web.app.test_client()


if __name__ == '__main__':
    import argparse

    argparser = argparse.ArgumentParser(
        description='Service that allows automatic migration of data to the CKAN DataStore',
        epilog='''"He reached out and pressed an invitingly large red button on a nearby panel.
                The panel lit up with the words Please do not press this button again."''')

    argparser.add_argument('config', metavar='CONFIG', type=file,
                       help='configuration file')
    args = argparser.parse_args()

    os.environ['JOB_CONFIG'] = args.config.name
    serve()
