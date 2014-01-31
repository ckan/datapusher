import ckanserviceprovider.web as web
import datapusher.jobs as jobs

# check whether jobs have been imported properly
assert(jobs.push_to_datastore)

web.configure()
app = web.app

if __name__ == "__main__":
    import logging
    import os
    port = os.environ.get('PORT', 8800)
    debug = os.environ.get('DEBUG', False)
    host = os.environ.get('HOST', '0.0.0.0')
    logging.basicConfig(level=logging.NOTSET)
    app.run(host=host, port=port, debug=debug)

