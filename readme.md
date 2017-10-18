# QMK Compiler API

JSON API for building a customized firmware.

## Goals

* Make it easy for apps to compile custom firmware
* Generate a compiled firmware for any QMK keyboard

# How Do I Use This API?

The root of the API's hostname will always redirect to the current documentation: http://compile.clueboard.co/

# How Do I Run My Own Copy?

To run your own copy you first need to setup an environment suitable for running the various services. These are documented in the sections below.

## Set Up Your Compilation Environment

If you have not already setup your build environment for QMK, you should
do so by [following the instructions](https://github.com/jackhumbert/qmk_firmware/blob/master/readme.md) provided by QMK.

## Set up Redis

We use [Redis Queue](http://python-rq.org) to decouple compiling the firmware from the webserver. It also handles administrative tasks like cleaning up old firmware hexes. Installing and administering Redis in a production environment is beyond the scope of this document.

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

# Compiler API Overview

The API consists of 4 services:

* [Redis](https://redis.io)
* [Minio](https://minio.io)
* [Worker](https://github.com/qmk/qmk_compiler_worker)
* [API](https://github.com/qmk/qmk_compiler_api)

To get started you will need to run all of them. We have helper scripts (documented below) to make this easier.

To run these services you'll need a local copy of Python 3 (tested with 3.5 and 3.6, but should work on 3.4 as well) and you will need to install flask. If you're not sure, you probably have python installed already, and can install flask and all the dependencies with:

    $ sudo pip3 install -r requirements.txt

If that fails you will need to install python 3 and pip.

Once you've installed the pre-requisites you should have running copies of Redis and Minio.

Note: In some environments Minio does not automatically start, you can use [`bin/start_minio`](bin/start_minio) to start the minio service in that case.

Once Redis and Minio are running you can use [`bin/start_dev_server`](bin/start_dev_server) to start the Worker and the API service.

Alternative: Docker
-------------------

The Production API runs in a docker environment and as such there are pre-written Dockerfiles for those images. If you are more comfortable working with docker these may be a better choice for you.

(Note: This section needs some love from someone that uses docker for development purposes.)


Deploying To Production
-----------------------

The development web server is not suitable for exposure to the internet. Deploying this in a configuration suitable for the public internet is beyond the scope of this document. However, you can use any standard WSGI stack to deploy this behind.

You may find the Dockerfile included with both the Worker and the API useful, as these are the files that setup the Docker images we use in production.
