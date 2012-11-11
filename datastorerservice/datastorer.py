import os

import ckanserviceprototype.web as web
import ckanserviceprototype.job as job
import ckanserviceprototype.util as util


@job.sync
def echo(task_id, input):
    if input['data'].startswith('>'):
        raise util.JobError('do not start message with >')
    return '>' + input['data']


if __name__ == '__main__':
    import argparse

    argparser = argparse.ArgumentParser(
        description='Service that allows automatic migration of data to the CKAN DataStore',
        epilog='"He reached out and pressed an invitingly large red button on a nearby panel. The panel lit up with the words Please do not press this button again."')

    argparser.add_argument('config', metavar='CONFIG', type=file,
                       help='configuration file')
    args = argparser.parse_args()

    os.environ['JOB_CONFIG'] = args.config.name

    web.configure()
    web.app.run()
