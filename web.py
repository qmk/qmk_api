import json
import logging
from decimal import Decimal
from io import BytesIO
from os.path import exists
from os import stat, remove, makedirs, environ
from time import strftime, time, localtime

import requests
from collections import OrderedDict
from codecs import open as copen
from flask import jsonify, Flask, redirect, request, send_file
from flask import make_response
from flask.json import JSONEncoder
from flask_cors import CORS
from rq import Queue

import qmk_redis
import qmk_storage
from kle2xy import KLE2xy
from qmk_compiler import compile_firmware, redis, ping
from update_kb_redis import update_kb_redis

if exists('version.txt'):
    __VERSION__ = open('version.txt').read()
else:
    __VERSION__ = '__UNKNOWN__'

UPDATE_API=environ.get('UPDATE_API', 'false') == 'true'


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
app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
app.config['JSON_SORT_KEYS'] = False
cache_dir = 'kle_cache'
gist_url = 'https://api.github.com/gists/%s'
cors = CORS(app, resources={'/v*/*': {'origins': '*'}})
rq = Queue(connection=redis)


## Helper functions
def error(message, code=400, **kwargs):
    """Return a structured JSON error message.
    """
    kwargs['message'] = message
    return jsonify(kwargs), code


def get_job_metadata(job_id):
    """Fetch a job's metadata from the file store.
    """
    json_text = qmk_storage.get('%s/%s.json' % (job_id, job_id))
    return json.loads(json_text)


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
            logging.warning('Removing zero-length cache file %s', cache_file)
            remove(cache_file)
        elif file_age < 30:
            logging.info('Using cache file %s (%s < 30)', cache_file, file_age)
            return copen(cache_file, encoding='UTF-8').read()
        else:
            headers['If-Modified-Since'] = strftime('%a, %d %b %Y %H:%M:%S %Z', localtime(file_stat.st_mtime))
            logging.warning('Adding If-Modified-Since: %s to headers.', headers['If-Modified-Since'])

    keyboard = requests.get(gist_url % gist_id, headers=headers)

    if keyboard.status_code == 304:
        logging.debug("Source for %s hasn't changed, loading from disk.", cache_file)
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
                del(qmk_key['label'])

            layout.append(qmk_key)

    return layout


## Views
@app.route('/', methods=['GET'])
def root():
    """Serve up the documentation for this API.
    """
    return redirect('https://docs.api.qmk.fm/')


@app.route('/v1', methods=['GET'])
def GET_v1():
    """Return the API's status.
    """
    return jsonify({
        'children': ['compile', 'converters', 'keyboards'],
        'last_ping': qmk_redis.get('qmk_api_last_ping'),
        'queue_length': len(rq),
        'status': 'running',
        'version': __VERSION__
    })


@app.route('/v1/healthcheck', methods=['GET'])
def GET_v1_healthcheck():
    """Checks over the health of the API.

    Note: This is used for operational purposes. Please don't hit it on the
    live api.qmk.fm site without talking to us first. Most of this
    information is available at the /v1 endpoint as well.
    """
    rq.enqueue(ping, at_front=True)

    return jsonify({
        'last_ping': qmk_redis.get('qmk_api_last_ping'),
        'queue_length': len(rq),
        'queued_job_ids':  rq.job_ids,
        'queued_jobs': rq.jobs,
        'status': 'running',
        'version': __VERSION__
    })


@app.route('/v1/update', methods=['GET'])
def GET_v1_update():
    """Triggers an update of the API.
    """
    result = {
        'result': UPDATE_API,
        'last_ping': qmk_redis.get('qmk_api_last_ping'),
        'queue_length': len(rq),
        'queued_job_ids':  rq.job_ids,
        'status': 'running',
        'version': __VERSION__
    }

    if UPDATE_API:
        rq.enqueue(update_kb_redis)

    return jsonify(result)


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

    try:
        kle = KLE2xy(raw_code)
    except Exception as e:
        logging.error('Could not parse KLE raw data: %s', raw_code)
        logging.exception(e)
        return error('Could not parse KLE raw data.')  # FIXME: This should be better

    keyboard = OrderedDict(
        keyboard_name=kle.name,
        url='',
        maintainer='qmk',
        bootloader='',
        width=kle.columns,
        height=kle.rows,
        layouts={'LAYOUT': {'layout': 'LAYOUT_JSON_HERE'}}
    )
    keyboard = json.dumps(keyboard, indent=4, separators=(', ', ': '), sort_keys=False, cls=CustomJSONEncoder)
    layout = json.dumps(kle_to_qmk(kle), separators=(', ', ':'), cls=CustomJSONEncoder)
    keyboard = keyboard.replace('"LAYOUT_JSON_HERE"', layout)
    response = make_response(keyboard)
    response.mimetype = app.config['JSONIFY_MIMETYPE']

    return response


@app.route('/v1/keyboards', methods=['GET'])
def GET_v1_keyboards():
    """Return a list of keyboards
    """
    json_blob = qmk_redis.get('qmk_api_keyboards')
    return jsonify(json_blob)


@app.route('/v1/keyboards/all', methods=['GET'])
def GET_v1_keyboards_all():
    """Return JSON showing all available keyboards and their layouts.
    """
    allkb = qmk_redis.get('qmk_api_kb_all')
    if allkb:
        return jsonify(allkb)
    return error('An unknown error occured', 500)


@app.route('/v1/keyboards/<path:keyboard>', methods=['GET'])
def GET_v1_keyboards_keyboard(keyboard):
    """Return JSON showing data about a keyboard
    """
    keyboards = qmk_redis.get('qmk_api_last_updated')
    keyboards['keyboards'] = {}

    for kb in keyboard.split(','):
        kb_data = qmk_redis.get('qmk_api_kb_'+kb)
        if kb_data:
            keyboards['keyboards'][kb] = kb_data

    if not keyboards['keyboards']:
        return error('No such keyboard: ' + keyboard, 404)

    return jsonify(keyboards)


@app.route('/v1/keyboards/<path:keyboard>/readme', methods=['GET'])
def GET_v1_keyboards_keyboard_readme(keyboard):
    """Returns the readme for a keyboard.
    """
    readme = qmk_redis.get('qmk_api_kb_%s_readme' % (keyboard))

    response = make_response(readme)
    response.mimetype = 'text/markdown'

    return response


@app.route('/v1/keyboards/<path:keyboard>/keymaps/<string:keymap>', methods=['GET'])
def GET_v1_keyboards_keyboard_keymaps_keymap(keyboard, keymap):
    """Return JSON showing data about a keyboard's keymap
    """
    keyboards = qmk_redis.get('qmk_api_last_updated')
    keyboards['keyboards'] = {}

    for kb in keyboard.split(','):
        kb_data = qmk_redis.get('qmk_api_kb_'+kb)
        if kb_data:
            keymaps = {}
            keymap_list = kb_data['keymaps'] if keymap == 'all' else keymap.split(',')

            for km in keymap_list:
                keymaps[km]  = qmk_redis.get('qmk_api_kb_%s_keymap_%s' % (kb, km))

            if not keymaps:
                return error('No such keymap: ' + keymap, 404)

            kb_data['keymaps'] = keymaps
            keyboards['keyboards'][kb] = kb_data

    if not keyboards['keyboards']:
        return error('No such keyboard: ' + keyboard, 404)

    return jsonify(keyboards)


@app.route('/v1/keyboards/<path:keyboard>/keymaps/<string:keymap>/readme', methods=['GET'])
def GET_v1_keyboards_keyboard_keymaps_keymap_readme(keyboard, keymap):
    """Returns the readme for a keymap.
    """
    readme = qmk_redis.get('qmk_api_kb_%s_keymap_%s_readme' % (keyboard, keymap))

    response = make_response(readme)
    response.mimetype = 'text/markdown'

    return response


@app.route('/v1/keyboards/build_status', methods=['GET'])
def GET_v1_keyboards_build_status():
    """Returns a dictionary of keyboard/layout pairs. Each entry is True if the keyboard works in configurator and
    false if it doesn't.
    """
    json_blob = qmk_redis.get('qmk_api_keyboards_tested')
    return jsonify(json_blob)


@app.route('/v1/keyboards/build_log', methods=['GET'])
def GET_v1_keyboards_build_log():
    """Returns a dictionary of keyboard/layout pairs. Each entry is a dictionary with the following keys:

    * `works`: Boolean indicating whether the compile was successful
    * `message`: The compile output for failed builds
    """
    json_data = {}
    failed = qmk_redis.get('qmk_api_keyboards_failed')

    for name, keyboard in qmk_redis.get('qmk_api_keyboards_tested').items():
        json_data[name] = {'works': keyboard, 'message': 'Keyboard compiled successfully.' if keyboard else 'Unknown compile error!'}
        if name in failed:
            json_data[name]['message'] = failed[name]['message']

    return jsonify(json_data)


@app.route('/v1/keyboards/error_log', methods=['GET'])
def GET_v1_keyboards_error_log():
    """Return the error log from the last run.
    """
    json_blob = qmk_redis.get('qmk_api_update_error_log')

    return jsonify(json_blob)


@app.route('/v1/compile', methods=['POST'])
def POST_v1_compile():
    """Enqueue a compile job.
    """
    data = request.get_json(force=True)
    if not data:
        return error("Invalid JSON data!")

    if '.' in data['keyboard'] or '/' in data['keymap']:
        return error("Fuck off hacker.", 422)

    job = compile_firmware.delay(data['keyboard'], data['keymap'], data['layout'], data['layers'])
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
            logging.error('Unknown job status!')
            status = 'unknown'
        return jsonify({
            'created_at': job.created_at,
            'enqueued_at': job.enqueued_at,
            'id': job.id,
            'is_failed': job.is_failed or (job.result and job.result.get('returncode') != 0),
            'status': status,
            'result': job.result
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

    if 'firmware_filename' in job['result']:
        firmware = qmk_storage.get_fd('%(id)s/%(firmware_filename)s' % job['result'])
        return send_file(firmware, mimetype='application/octet-stream', as_attachment=True, attachment_filename=job['result']['firmware_filename'])

    return error("Compile job not finished or other error.", 422)


@app.route('/v1/compile/<string:job_id>/source', methods=['GET'])
def GET_v1_compile_job_id_src(job_id):
    """Download a completed compile job.
    """
    job = get_job_metadata(job_id)
    if not job:
        return error("Compile job not found", 404)

    if job['result']['firmware']:
        source_zip = qmk_storage.get_fd('%(id)s/%(source_archive)s' % job['result'])
        return send_file(source_zip, mimetype='application/octet-stream', as_attachment=True, attachment_filename=job['result']['source_archive'])

    return error("Compile job not finished or other error.", 422)


if __name__ == '__main__':
    # Start the webserver
    app.run(debug=True)
