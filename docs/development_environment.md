# Development Environment Setup

The QMK Compile API consists of a few movings parts:

* [Redis](http://redis.io)
* [Minio](http://minio.io)
* QMK Compiler Worker
* QMK Compiler API

To get these working together you'll need to install Redis and Minio along with QMK Compiler's dependencies.

# Redis

We use [RQ](http://python-rq.org) to decouple compiling the firmware from the webserver. It also handles administrative tasks like cleaning up old firmware hexes. Installing and administering Redis in a production environment is beyond the scope of this document.

For development purposes, you can simply install and run redis with the default configuration.

#### macOS (Homebrew)

On macOS you can use [homebrew](http://brew.sh) to install redis. You only
have to do this once.

    $ brew install redis
    $ brew services start redis

#### Debian, Ubuntu

The version of redis in the repositories is most likely outdated.
[You may want to build the latest version from source
instead.](http://redis.io/topics/quickstart)

    $ sudo apt-get update
    $ sudo apt-get install redis-server
    $ sudo service redis-server start

#### Other Operating Systems

If you have experience setting up Redis on a system not listed, please submit a PR with instructions so that others may benefit from your experience.

# Minio

Minio is a scalable object storage server with an API compatible with Amazon's S3. For development purposes you can run a single instance with no special configuration.

Once you've installed Minio you can use `bin/start_minio` to start an instance of minio configured for the QMK Compiler development environment. You'll want to do this in a separate terminal from the other services as Minio is very chatty.

#### macOS (Homebrew)

On macOS you can use [homebrew](http://brew.sh) to install Minio. You only have to do this once.

    $ brew install minio

#### Docker

From <https://minio.io>:

    $ docker run -p 9000:9000 --name minio1 -v /mnt/data:/data -v /mnt/config:/root/.minio minio/minio server /data

# Python 3

QMK Compiler is written in [Python 3](http://python.org). It was developed against 3.6 but should work on any release after 3.5. Your computer probably has Python already, but if not [install it](https://www.python.org/downloads/).

# Zip

QMK Compiler needs the zip and unzip binaries to be available. These are probably already on your system but if not you will need to install them.

# Code Checkout

There are two repositories you'll need to clone to work on QMK Compiler. Make sure to put them in the same directory so they can find each other.

    $ git clone https://github.com/qmk/qmk_compiler_api.git
    $ git clone https://github.com/qmk/qmk_compiler_worker.git

# Virtualenv

While it is possible to install the dependencies system wide you will keep your development environment cleaner if you develop inside a virtualenv. We've provided a script to make this setup easy:

    $ bin/setup_virtualenv

Once you have setup your virtualenv follow the instructions for activating it. You need to make sure it is active before you run the server.

    $ source activate-3.6

# Running QMK Compiler

First start Minio:

    $ bin/start_minio

In another terminal start the backend and worker:

    $ bin/start_dev_server

Finally, use the `test_compile` script to submit a compile job:

    $ bin/test_compile json_data
