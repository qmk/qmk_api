import json
import logging
import qmk_redis
import qmk_storage
from flask import jsonify, Flask, redirect, request, send_file
from flask_cors import CORS
from os.path import exists
from rq import Queue
from qmk_compiler import compile_firmware, redis
from qmk_storage import get
from time import strftime

if exists('version.txt'):
    __VERSION__ = open('version.txt').read()
else:
    __VERSION__ = '__UNKNOWN__'

# Useful objects
app = Flask(__name__)
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


## Views
@app.route('/', methods=['GET'])
def root():
    """Serve up the documentation for this API.
    """
    return redirect('https://docs.compile.qmk.fm/')


@app.route('/v1', methods=['GET'])
def GET_v1():
    """Return the API's status.
    """
    return jsonify({
        'status': 'running',
        'version': __VERSION__
    })


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
    keyboards = {
        'last_updated': qmk_redis.get('qmk_api_last_updated'),
        'keyboards': {}
    }
    for kb in keyboard.split(','):
        kb_data = qmk_redis.get('qmk_api_kb_'+kb)
        if kb_data:
            keyboards['keyboards'][kb] = kb_data

    if not keyboards['keyboards']:
        return error('No such keyboard: ' + keyboard, 404)

    return jsonify(keyboards)


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
            'is_failed': job.is_failed or job.result.get('returncode') != 0,
            'status': status,
            'result': job.result
        })

    # Check for cached json if it's not in redis
    job = get_job_metadata(job_id)
    if job:
        return jsonify(job)

    # Couldn't find it
    return error("Compile job not found", 404)


@app.route('/v1/compile/<string:job_id>/hex', methods=['GET'])
def GET_v1_compile_job_id_hex(job_id):
    """Download a compiled firmware
    """
    job = get_job_metadata(job_id)
    if not job:
        return error("Compile job not found", 404)

    if job['result']['firmware']:
        return send_file(job['result']['firmware'], mimetype='application/octet-stream', as_attachment=True, attachment_filename=job['result']['firmware_filename'])

    return error("Compile job not finished or other error.", 422)


@app.route('/v1/compile/<string:job_id>/source', methods=['GET'])
def GET_v1_compile_job_id_src(job_id):
    """Download a completed compile job.
    """
    job = get_job_metadata(job_id)
    if not job:
        return error("Compile job not found", 404)

    if job['result']['firmware']:
        source_zip = qmk_storage.get('%(id)s/%(source_archive)s' % job['result'])
        return send_file(source_zip, mimetype='application/octet-stream', as_attachment=True, attachment_filename=job['result']['source_archive'])

    return error("Compile job not finished or other error.", 422)


if __name__ == '__main__':
    # Start the webserver
    app.run(debug=True)
