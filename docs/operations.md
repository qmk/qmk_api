# QMK API Operations

This page documents useful operational information you should know if you're helping to run the QMK API or running your own instance of the QMK API.

## Production Infrastructure

The QMK API is hosted on a Rancher Cluster that has been provided by Clueboard. All of the QMK API containers are located in the `qmk-api` Stack. There are 5 containers in total:

* `api` - The service that handles HTTP requests from clients
* `compiler` - The [RQ](https://python-rq.org/docs/) worker process, where compilation and various maintenance tasks happen
* `qmk-bot` - The service that receives webhook triggers from github, to kick off maintenance tasks
* `redis` - An instance of redis, used for [RQ](https://python-rq.org/docs/) and metadata storage
* `redis-lb` - An haproxy instance that load balances redis traffic

## Code Deployments

We use [Docker Hub](https://hub.docker.com) to build and distribute containers for the production infrastructure. Every PR merged into our GitHub repositories will result in a new container being built and available.

The critical path for code is:

1. A developer submits a PR to [qmk_api](https://github.com/qmk/qmk_api), [qmk_bot](https://github.com/qmk/qmk_bot), and/or [qmk_compiler](https://github.com/qmk/qmk_compiler)
2. A QMK Collaborator merges that PR into master
3. Docker Hub builds a new container. Progress of the build is available publicly:
   * [qmk_api](https://hub.docker.com/r/skullydazed/qmk_api/builds/)
   * [qmk_bot](https://hub.docker.com/r/qmkfm/qmk_bot/builds/)
   * [qmk_compiler](https://hub.docker.com/r/skullydazed/qmk_compiler/builds/)
4. A QMK Member deploys that container using Rancher

## Configuration

QMK API services are configured using environment variables. This allows us to keep sensitive information out of the publically available containers. In the future we should use [Rancher Secrets](https://rancher.com/docs/rancher/v1.5/en/cattle/secrets/), but we have not yet written support for that.

### QMK API and Compiler Configuration

The following environment variables may be used in both the API and the Compiler.

| Key | Default Value | Notes |
|-----|---------------|-------|
|`REDIS_HOST`|`redis.qmk-api`|The host (and optionally port) that redis can be reached on|
|`STORAGE_ENGINE`|`s3`|The storage engine for compiled firmware and source. `s3` or `filesystem`|
|`FILESYSTEM_PATH`|`firmwares`|The directory to use when `STORAGE_ENGINE`==`filesystem`|
|`S3_HOST`|`http://127.0.0.1:9000`|The URL for an S3-like storage service|
|`S3_LOCATION`|`nyc3`|The location for your S3-like storage service|
|`S3_BUCKET`|`qmk`|The bucket to store firmware and source in|
|`S3_ACCESS_KEY`|`minio_dev`|The access key for your S3 storage|
|`S3_SECRET_KEY`|`minio_dev_secret`|The secret key for your S3 storage|
|`STORAGE_TIME_HOURS`|`48`|How many hours to store compiled firmware and source|

### QMK Bot Configuration

There is currently no configuration for the QMK Bot.
