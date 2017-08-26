from os.path import exists
from qmk_compiler import compile_firmware, redis
from flask import jsonify, Flask, render_template, request, send_file
from flask_cors import CORS, cross_origin
from rq import Queue

if exists('version.txt'):
    __VERSION__ = open('version.txt').read()
else:
    __VERSION__ = '__UNKNOWN__'

app = Flask(__name__)
cors = CORS(app, resources={'/v*/*': {'origins': '*'}})
rq = Queue(connection=redis)

# Figure out what keyboards are available
app.config['COMPILE_TIMEOUT'] = 60

## Helper functions
def error(message, code=400, **kwargs):
    """Return a structured JSON error message.
    """
    kwargs['message'] = message
    return jsonify(kwargs), code


## Views
@app.route('/', methods=['GET'])
def root():
    """Serve up the documentation for this API.
    """
    return render_template('index.html')


@app.route('/v1', methods=['GET'])
def v1():
    """Serve up the documentation for this API.
    """
    return jsonify({
        'status': 'running',
        'version': __VERSION__
    })


@app.route('/v1/compile', methods=['POST'])
def POST_v1_compile():
    """Enqueue a compile job.
    """
    data = request.get_json(force=True)
    if not data:
        return error("Invalid JSON data!")

    if '/' in data['keyboard'] or '/' in data['subproject'] or '/' in data['keymap']:
        return error("Fuck off hacker.", 422)

    job = compile_firmware.delay(data['keyboard'], data['subproject'], data['keymap'], data['layers'])
    return jsonify({'enqueued': True, 'job_id': job.id})


@app.route('/v1/compile/<string:job_id>', methods=['GET'])
def POST_v1_compile_job_id(job_id):
    """Fetch the status of a compile job.
    """
    job = rq.fetch_job(job_id)
    if not job:
        return error("Compile job not found", 404)

    return jsonify({
        'created_at': job.created_at,
        'enqueued_at': job.enqueued_at,
        'id': job.id,
        'is_failed': job.is_failed,
        'is_finished': job.is_finished,
        'is_queued': job.is_queued,
        'is_started': job.is_started,
        'result': job.result
    })


@app.route('/v1/compile/<string:job_id>/hex', methods=['GET'])
def POST_v1_compile_job_id_hex(job_id):
    """Download a compiled firmware
    """
    job = rq.fetch_job(job_id)
    if not job:
        return error("Compile job not found", 404)

    if job.is_finished and job.result['firmware']:
        filename = '%(keyboard)s_%(subproject)s_%(keymap)s.hex' % job.result
        return send_file('firmwares/%s/%s' % (job_id, filename), 'application/octet-stream', as_attachment=True, attachment_filename=filename)

    # Send a 400 if we can't find the job or firmware.
    return error("Compile job not finished or other error.", 422)


@app.route('/v1/compile/<string:job_id>/src', methods=['GET'])
def POST_v1_compile_job_id_src(job_id):
    """Download a completed compile job.
    """
    if exists('firmwares/%s/qmk_firmware.zip' % job_id):
        return send_file('firmwares/%s/qmk_firmware.zip' % job_id, 'application/octet-stream', as_attachment=True, attachment_filename='qmk_firmware.zip')

    return error("Compile job not finished or other error.", 404)


if __name__ == '__main__':
    # Start the webserver
    app.run(debug=True)
