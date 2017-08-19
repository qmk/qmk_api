QMK Configurator
================

Web based API for building a customized firmware.

Goals
-----

* Make it easy for web apps to compile custom firmware
* Generate a pre-compiled firmware for any QMK keyboard

How Do I Run My Own Copy?
=========================

The API is a simple flask application. To get started you will need
a local copy of Python 3 (tested with 3.5.2, but should work on 3.4 as well)
and you will need to install flask. If you're not sure, you probably 
have python installed already, and can install the dependencies with:

    $ sudo pip3 install -r requirements.txt
    
If that fails you will need to install python 3.

Set Up Your Build Environment
-----------------------------

If you have not already setup your build environment for QMK, you should
do so by [following the instructions](https://github.com/jackhumbert/qmk_firmware/blob/master/readme.md) provided by QMK.

Setting up Redis
----------------

We use [RQ](http://python-rq.org) to decouple compiling the firmware from
the webserver. It also handles administrative tasks like cleaning up old
firmware hexes. Installing and administering Redis in a production environment
is beyond the scope of this document.

For development purposes, you can simply install and run redis with the default
configuration.

**macOS (Homebrew)**

On macOS you can use [homebrew](http://brew.sh) to install redis. You only 
have to do this once.

    $ brew install redis
    $ brew services start redis
    
**Debian, Ubuntu**

The version of redis in the repositories is most likely outdated. 
[You may want to build the latest version from source 
instead.](http://redis.io/topics/quickstart)

    $ sudo apt-get update
    $ sudo apt-get install redis-server
    $ sudo service redis-server start

**Other Operating Systems**

If you have experience setting up Redis on a system not listed, please
submit a PR with instructions so that others may benefit from your experience.

Starting The RQ Worker
----------------------

To process the jobs that compile firmwares run `rq worker`.

Starting The Development Web Server
-----------------------------------

After installing the pre-requisites above run the "web.py" script.

    $ python web.py
     * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)

(There may be other lines as well, as long as they are not errors
you can safely disregard them for now.)

Open up the URL specified and you should be looking at documentation 
for the API.

Deploying To Production
-----------------------

The development web server is not suitable for exposure to the internet.
Deploying this in a configuration suitable for the public internet is beyond
the scope of this document. However, you can use any standard WSGI stack
to deploy this behind. 
