import json
import logging
from collections import OrderedDict
from codecs import open as copen
from decimal import Decimal
from os.path import exists
from os import stat, remove, makedirs, environ
from time import strftime, time, localtime
from urllib.parse import urlparse

import graphyte
import requests
from flask import jsonify, Flask, redirect, request, send_file
from flask import has_request_context, make_response, request
from flask.json import JSONEncoder
from flask.logging import default_handler
from flask_cors import CORS
from flask_graphite import FlaskGraphite
from rq import Queue

import qmk_redis
import qmk_storage
from kle2xy import KLE2xy
from qmk_commands import keymap_skeleton
from qmk_compiler import compile_json, redis, ping
from update_kb_redis import update_kb_redis

if exists('version.txt'):
    with open('version.txt') as version_file:
        __VERSION__ = version_file.read()
else:
    __VERSION__ = '__UNKNOWN__'

UPDATE_API = environ.get('UPDATE_API', 'false') == 'true'  # Whether or not the /update route is enabled
CHECK_TIMEOUT = environ.get('CHECK_TIMEOUT', 300)  # How long the checks need to fail before we are degraded
FLASK_GRAPHITE_HOST = environ.get('FLASK_GRAPHITE_HOST', 'qmk_metrics_aggregator')
FLASK_GRAPHITE_PORT = int(environ.get('FLASK_GRAPHITE_PORT', 2023))
QUERY_GRAPHITE_HOST = environ.get('QUERY_GRAPHITE_HOST', 'graphite')
QUERY_GRAPHITE_PORT = int(environ.get('QUERY_GRAPHITE_PORT', 8080))
KEYMAP_JSON_DOCUMENTATION = """This file is a configurator export. It can be used directly with QMK's source code.

To setup your QMK environment check out the tutorial: https://docs.qmk.fm/#/newbs

You can convert this file to a keymap.c using this command: `qmk json2c %(keyboard)s_%(keymap)s.json`

You can compile this keymap using this command: `qmk compile %(keyboard)s_%(keymap)s.json`"""

## Configure logging
class RequestFormatter(logging.Formatter):
    def format(self, record):
        if has_request_context():
            record.url = request.url
            record.remote_addr = request.remote_addr
        else:
            record.url = None
            record.remote_addr = None

        return super().format(record)

default_handler.setFormatter(RequestFormatter(
    '[%(asctime)s] %(remote_addr)s requested %(url)s\n'
    '%(levelname)s in %(module)s: %(message)s'
))

root = logging.getLogger()
root.addHandler(default_handler)

## Classes
class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, Decimal):
                if obj % 2 in (Decimal(0), Decimal(1)):
                    return int(obj)
                return float(obj)
        except TypeError:
            pass
        return JSONEncoder.default(self, obj)


# Useful objects
metric_sender = FlaskGraphite()
app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
app.config['JSON_SORT_KEYS'] = False
app.config['FLASK_GRAPHITE_HOST'] = FLASK_GRAPHITE_HOST
app.config['FLASK_GRAPHITE_PORT'] = FLASK_GRAPHITE_PORT
app.config['FLASK_GRAPHITE_PREFIX'] = environ.get('FLASK_GRAPHITE_PREFIX', '')
app.config['FLASK_GRAPHITE_GROUP'] = environ.get('FLASK_GRAPHITE_GROUP', 'qmk_api')
app.config['FLASK_GRAPHITE_AUTORECONNECT'] = environ.get('FLASK_GRAPHITE_AUTORECONNECT', 'true') == 'true'
app.config['FLASK_GRAPHITE_METRIC_TEMPLATE'] = environ.get('FLASK_GRAPHITE_METRIC_TEMPLATE', 'url_rule')
cache_dir = 'kle_cache'
gist_url = 'https://api.github.com/gists/%s'
cors = CORS(app, resources={'/v*/*': {'origins': '*'}})
rq = Queue(connection=redis)
api_status = {
    'last_ping': qmk_redis.get('qmk_api_last_ping'),
    'queue_length': len(rq),
    'status': 'starting',
    'version': __VERSION__,
}

graphyte.init(FLASK_GRAPHITE_HOST, FLASK_GRAPHITE_PORT)
metric_sender.init_app(app)


## Helper functions
def check_pings():
    """Check the ping values and update api_status with them.
    """
    api_status['queue_length'] = len(rq)
    for redis_key in ('qmk_api_last_ping', 'qmk_api_tasks_ping'):
        key = redis_key.replace('qmk_api_', '')
        value = qmk_redis.get(redis_key)
        api_status[key] = value

        if value:
            if time() - float(value) > CHECK_TIMEOUT:
                api_status['status'] = 'degraded'
                api_status['status_%s' % key] = 'degraded'
            else:
                api_status['status'] = 'running'
                api_status['status_%s' % key] = 'good'
        else:
            api_status['status'] = 'degraded'
            api_status['status_%s' % key] = 'degraded'


def client_ip():
    """Returns the client's IP address.
    """
    return request.headers.get('X-Forwarded-For', request.remote_addr)


def request_hostname():
    """Returns the hostname of the request.
    """
    return urlparse(request.base_url).hostname


def error(message, code=400, **kwargs):
    """Return a structured JSON error message.
    """
    kwargs['code'] = code
    kwargs['message'] = message
    return jsonify(kwargs), code


def get_job_metadata(job_id):
    """Fetch a job's metadata from the file store.
    """
    json_text = qmk_storage.get('%s/%s.json' % (job_id, job_id))
    return json.loads(json_text)


def fetch_graphite_sum(target, from_time='-24h', until_time='-1s'):
    """Returns summed values from graphite.

    Parameters are as described by the graphite API:
        <https://graphite-api.readthedocs.io/en/latest/api.html#the-metrics-api>
    """
    graphite_url = f'http://{QUERY_GRAPHITE_HOST}:{QUERY_GRAPHITE_PORT}/render'
    query_args = {
        'target': target,
        'format': 'json',
        'from': from_time,
        'until': until_time
    }
    rawdata = requests.get(graphite_url, params=query_args)
    data = {}

    for line in rawdata.json():
        datapoint = 0
        for dp in line['datapoints']:
            if dp[0] is not None:
                datapoint += dp[0]

        if datapoint:
            data[line['target']] = datapoint

    return data


def fetch_kle_json(gist_id):
    """Returns the JSON for a keyboard-layout-editor URL.
    """
    cache_file = '/'.join((cache_dir, gist_id))
    headers = {}

    if exists(cache_file):
        # We have a cached copy
        file_stat = stat(cache_file)
        file_age = time() - file_stat.st_mtime

        if file_stat.st_size == 0:
            app.logger.warning('Removing zero-length cache file %s', cache_file)
            remove(cache_file)
        elif file_age < 30:
            app.logger.info('Using cache file %s (%s < 30)', cache_file, file_age)
            return copen(cache_file, encoding='UTF-8').read()
        else:
            headers['If-Modified-Since'] = strftime('%a, %d %b %Y %H:%M:%S %Z', localtime(file_stat.st_mtime))
            app.logger.warning('Adding If-Modified-Since: %s to headers.', headers['If-Modified-Since'])

    keyboard = requests.get(gist_url % gist_id, headers=headers)

    if keyboard.status_code == 304:
        app.logger.debug("Source for %s hasn't changed, loading from disk.", cache_file)
        return copen(cache_file, encoding='UTF-8').read()

    keyboard = keyboard.json()

    for file in keyboard['files']:
        keyboard_text = keyboard['files'][file]['content']
        break  # First file wins, hope there's only one...

    if not exists(cache_dir):
        makedirs(cache_dir)

    with copen(cache_file, 'w', encoding='UTF-8') as fd:
        fd.write(keyboard_text)  # Write this to a cache file

    return keyboard_text


def kle_to_qmk(kle):
    """Convert a kle layout to qmk's layout format.
    """
    layout = []

    for row in kle:
        for key in row:
            if key['decal']:
                continue

            qmk_key = OrderedDict(
                label="",
                x=key['column'],
                y=key['row'],
            )

            if key['width'] != 1:
                qmk_key['w'] = key['width']
            if key['height'] != 1:
                qmk_key['h'] = key['height']
            if 'name' in key and key['name']:
                qmk_key['label'] = key['name'].split('\n', 1)[0]
            else:
                del (qmk_key['label'])

            layout.append(qmk_key)

    return layout


## Views
@app.route('/', methods=['GET'])
def root():
    """Serve up the documentation for this API.
    """
    if request_hostname() == 'install.qmk.fm':
        return redirect('https://raw.githubusercontent.com/qmk/qmk_firmware/refs/heads/bootstrap/util/env-bootstrap.sh')
    return redirect('https://docs.qmk.fm/#/api_docs')


@app.route('/install.sh', methods=['GET'])
def install():
    """Serve up the install script for the QMK CLI.
    """
    return redirect('https://raw.githubusercontent.com/qmk/qmk_firmware/refs/heads/bootstrap/util/env-bootstrap.sh')


@app.route('/v1', methods=['GET'])
def GET_v1():
    """Return the API's status.
    """
    check_pings()
    return jsonify({'children': ['compile', 'converters', 'keyboards', 'skeletons'], **api_status})


@app.route('/v1/healthcheck', methods=['GET'])
def GET_v1_healthcheck():
    """Checks over the health of the API.

    Note: This is used for operational purposes. Please don't hit it on the
    live api.qmk.fm site without talking to us first. Most of this
    information is available at the /v1 endpoint as well.
    """
    rq.enqueue(ping, at_front=True)
    check_pings()
    return jsonify(api_status)


@app.route('/v1/converters', methods=['GET'])
def GET_v1_converters():
    """Return the list of converters we support.
    """
    return jsonify({'children': ['kle']})


@app.route('/v1/converters/kle2qmk', methods=['POST'])
@app.route('/v1/converters/kle', methods=['POST'])
def POST_v1_converters_kle():
    """Convert a KLE layout to QMK's layout format.
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return error("Invalid JSON data!")

        if 'id' in data:
            gist_id = data['id'].split('/')[-1]
            raw_code = fetch_kle_json(gist_id)[1:-1]
        elif 'raw' in data:
            raw_code = data['raw']
        else:
            return error('You must supply either "id" or "raw" labels.')

        kle = KLE2xy(raw_code)

        keyboard = OrderedDict(
            keyboard_name=kle.name,
            url='',
            maintainer='qmk',
            layouts={'LAYOUT': {
                'layout': 'LAYOUT_JSON_HERE'
            }},
        )
        keyboard = json.dumps(keyboard, indent=4, separators=(', ', ': '), sort_keys=False, cls=CustomJSONEncoder)
        layout = json.dumps(kle_to_qmk(kle), separators=(', ', ':'), cls=CustomJSONEncoder)
        keyboard = keyboard.replace('"LAYOUT_JSON_HERE"', layout)
    except Exception as e:
        app.logger.error('Could not parse KLE raw data: %s', raw_code)
        app.logger.exception(e)
        return error('Could not parse KLE raw data: %s', e)

    response = make_response(keyboard)
    response.mimetype = app.config['JSONIFY_MIMETYPE']

    return response


@app.route('/v1/metrics/keyboards/days/<int:days>', methods=['GET'])
@app.route('/v1/metrics/keyboards', methods=['GET'])
def GET_v1_metrics_keyboards(days=1):
    """Return some data about the keyboards we've seen.
    """
    if days > 7:
        days = 7

    from_time = f'-{days}d'
    keyboards = fetch_graphite_sum(['qmk_cli.*.*.all_layouts','qmk_compiler.compile_json.*.all_layouts'], from_time=from_time)

    return jsonify(keyboards=keyboards)


@app.route('/v1/metrics/locations/days/<int:days>', methods=['GET'])
@app.route('/v1/metrics/locations', methods=['GET'])
def GET_v1_metrics_location(days=1):
    """Return some data about the locations users have reported from.
    """
    if days > 7:
        days = 7

    from_time = f'-{days}d'
    locations = fetch_graphite_sum('*.geoip.*', from_time=from_time)

    return jsonify(locations=locations)


@app.route('/v1/telemetry', methods=['POST'])
def POST_v1_telemetry():
    """Process a telemetry packet from the CLI.
    """
    base_metric = f'{gethostname()}.qmk_cli'
    data = request.get_json(force=True)

    if not data:
        return error("Invalid JSON data!")

    action = data.get('action')
    keyboard = data.get('keyboard')
    layout = data.get('layout')
    location_ok = data.get('location_ok')

    if action and keyboard and layout:
        metric_name = f'{base_metric}.{action}.{keyboard}'
        graphyte.send(f'{metric_name}.all_layouts', 1)
        graphyte.send(f'{metric_name}.{layout}', 1)

    if location_ok:
        ip_location = geolite2.lookup(client_ip())

        if ip_location:
            if ip_location.subdivisions:
                location_key = f'{ip_location.country}_{"_".join(ip_location.subdivisions)}'
            else:
                location_key = ip_location.country

            graphyte.send(f'{base_metric}.geoip.{location_key}', 1)

    return jsonify(message='Thanks for helping to improve QMK!')


@app.route('/v1/keyboards', methods=['GET'])
def GET_v1_keyboards():
    """Return a list of keyboards
    """
    keyboard_list = requests.get('https://keyboards.qmk.fm/v1/keyboard_list.json')
    return jsonify(keyboard_list.json()['keyboards'])


@app.route('/v1/keyboards/all', methods=['GET'])
def GET_v1_keyboards_all():
    """Return JSON showing all available keyboards and their layouts.
    """
    return redirect('https://keyboards.qmk.fm/v1/keyboards.json')


@app.route('/v1/keyboards/<path:keyboard>', methods=['GET'])
def GET_v1_keyboards_keyboard(keyboard):
    """Return JSON showing data about a keyboard
    """
    return redirect(f'https://keyboards.qmk.fm/v1/keyboards/<keyboard>/info.json')

@app.route('/v1/keyboards/<path:keyboard>/readme', methods=['GET'])
def GET_v1_keyboards_keyboard_readme(keyboard):
    """Returns the readme for a keyboard.
    """
    return redirect(f'https://keyboards.qmk.fm/v1/keyboards/<keyboard>/readme.md')


@app.route('/v1/keyboards/<path:keyboard>/keymaps/<string:keymap>', methods=['GET'])
def GET_v1_keyboards_keyboard_keymaps_keymap(keyboard, keymap):
    """Return JSON showing data about a keyboard's keymap

    Deprecated because it's unused and takes up valuable memory and processing time.
    """
    return error('No such keymap: ' + keymap, 404)


@app.route('/v1/keyboards/<path:keyboard>/keymaps/<string:keymap>/readme', methods=['GET'])
def GET_v1_keyboards_keyboard_keymaps_keymap_readme(keyboard, keymap):
    """Returns the readme for a keymap.

    Deprecated because it's unused and takes up valuable memory and processing time.
    """
    return error('No such keymap: ' + keymap, 404)


@app.route('/v1/keyboards/build_status', methods=['GET'])
def GET_v1_keyboards_build_status():
    """Returns a dictionary of keyboard/layout pairs. Each entry is True if the keyboard works in configurator and
    false if it doesn't.
    """
    json_blob = qmk_redis.get('qmk_api_keyboards_tested')
    return jsonify(json_blob)


@app.route('/v1/keyboards/build_log', methods=['GET'])
def GET_v1_keyboards_build_log():
    """Return the last build log for each keyboard. Each entry is a dictionary with the following keys:

    * `works`: Boolean indicating whether the compile was successful
    * `last_tested`: Unix timestamp of the last build
    * `message`: The compile output
    """
    json_data = qmk_redis.get('qmk_api_configurator_status')
    return jsonify(json_data)


@app.route('/v1/keyboards/build_summary', methods=['GET'])
def GET_v1_keyboards_build_summary():
    """Return the last build log for each keyboard, similar to the above but without the `message` entry.
    """
    json_data = qmk_redis.get('qmk_api_configurator_status')
    without_message = {kb: {k: v for (k, v) in status.items() if k != 'message'} for (kb, status) in json_data.items()}
    return jsonify(without_message)


@app.route('/v1/keyboards/<path:keyboard>/build_log', methods=['GET'])
def GET_v1_keyboards_keyboard_build_log(keyboard):
    """Return the last build log for the given keyboard.
    """
    json_data = qmk_redis.get('qmk_api_configurator_status').get(keyboard)
    return jsonify(json_data)


@app.route('/v1/keyboards/error_log', methods=['GET'])
def GET_v1_keyboards_error_log():
    """Return the error log from the last run.
    """
    json_blob = qmk_redis.get('qmk_api_update_error_log')

    return jsonify(json_blob)


@app.route('/v1/usb', methods=['GET'])
def GET_v1_usb():
    """Returns the list of USB device identifiers used in QMK.
    """
    return redirect(f'https://keyboards.qmk.fm/v1/usb.json')


@app.route('/v1/skeletons', methods=['GET'])
def GET_v1_skeletons():
    """Return the list of available skeletons.
    """
    return jsonify({'children': ['keymap']})


@app.route('/v1/skeletons/keymap', methods=['GET'])
def GET_v1_skeletons_keymap():
    """Returns a keymap skeleton.
    """
    return jsonify(keymap_skeleton())


@app.route('/v1/compile', methods=['POST'])
def POST_v1_compile():
    """Enqueue a compile job.
    """
    data = request.get_json(force=True)
    if not data:
        return error("Invalid JSON data!")

    if '.' in data['keyboard'] or '/' in data['keymap']:
        return error("Buzz off hacker.", 422)

    bad_keys = []
    for key in ('keyboard', 'keymap', 'layout', 'layers'):
        if key not in data:
            bad_keys.append(key)

    if bad_keys:
        return error("Invalid or missing keys: %s" % (', '.join(bad_keys),))

    if 'documentation' not in data:
        data['documentation'] = KEYMAP_JSON_DOCUMENTATION % data

    job = compile_json.delay(data, client_ip())
    return jsonify({'enqueued': True, 'job_id': job.id})


@app.route('/v1/compile/<string:job_id>', methods=['GET'])
def GET_v1_compile_job_id(job_id):
    """Fetch the status of a compile job.
    """
    # Check redis first.
    job = rq.fetch_job(job_id)
    if job:
        if job.is_finished:
            status = 'finished'
        elif job.is_queued:
            status = 'queued'
        elif job.is_started:
            status = 'running'
        elif job.is_failed:
            status = 'failed'
        else:
            app.logger.error('Unknown job status!')
            status = 'unknown'

        return jsonify({
            'created_at': job.created_at,
            'enqueued_at': job.enqueued_at,
            'id': job.id,
            'is_failed': job.is_failed or (job.result and isinstance(job.result, str)) or (job.result and job.result.get('returncode') != 0),
            'status': status,
            'result': job.result,
        })

    # Check for cached json if it's not in redis
    job = get_job_metadata(job_id)
    if job:
        return jsonify(job)

    # Couldn't find it
    return error("Compile job not found", 404)


@app.route('/v1/compile/<string:job_id>/download', methods=['GET'])
@app.route('/v1/compile/<string:job_id>/hex', methods=['GET'])
def GET_v1_compile_job_id_bin(job_id):
    """Download a compiled firmware.

    New clients should prefer the `/download` URL. `/hex` is deprecated and will be removed in a future version.
    """
    job = get_job_metadata(job_id)
    if not job:
        return error("Compile job not found", 404)

    return redirect(qmk_storage.get_public_url('%(id)s/%(firmware_filename)s' % job['result']))


@app.route('/v1/compile/<string:job_id>/keymap', methods=['GET'])
def GET_v1_compile_job_id_keymap(job_id):
    """Download the keymap for a completed compile job.
    """
    job = get_job_metadata(job_id)
    if not job:
        return error("Compile job not found", 404)

    return redirect(qmk_storage.get_public_url('%(id)s/%(keymap_archive)s' % job['result']))


@app.route('/v1/compile/<string:job_id>/source', methods=['GET'])
def GET_v1_compile_job_id_src(job_id):
    """Download the full source for a completed compile job.
    """
    job = get_job_metadata(job_id)
    if not job:
        return error("Compile job not found", 404)

    return redirect(qmk_storage.get_public_url('%(id)s/%(source_archive)s' % job['result']))


if __name__ == '__main__':
    # Start the webserver
    app.run(debug=True)
