# QMK Keymap Compiler API

This page describes the API for interacting with QMK Compiler. If you are an application developer you can use this API to compile firmware for any [QMK](http://qmk.fm) Keyboard.

## Overview

This service is an asynchronous API for compiling custom keymaps. You POST some JSON to the API, periodically check the status, and when your firmware has finished compiling you can download the resulting firmware and (if desired) source code for that firmware.

#### Example JSON Payload:

```
{
  "last_updated": "2017-11-01 22:18:53 PDT",
  "keyboards": {
    "clueboard/66": {
      "bootloader": "atmel-dfu",
      "identifier": "c1ed:2320:0001",
      "keyboard_folder": "clueboard/66",
      "keyboard_name": "Clueboard 66%",
      "last_updated": "2017-11-01 22:18:53 PDT",
      "maintainer": "skullydazed",
      "manufacturer": "Clueboard",
      "processor": "atmega32u4",
      "height": 5,
      "width": 16.5
      "layouts": {
        "KEYMAP": [ { "w": 1, "x": 0, "y": 0 }, { "w": 1, "x": 1, "y": 0 }, { "w": 1, "x": 2, "y": 0 }, { "w": 1, "x": 3, "y": 0 }, { "w": 1, "x": 4, "y": 0 }, { "w": 1, "x": 5, "y": 0 }, { "w": 1, "x": 6, "y": 0 }, { "w": 1, "x": 7, "y": 0 }, { "w": 1, "x": 8, "y": 0 }, { "w": 1, "x": 9, "y": 0 }, { "w": 1, "x": 10, "y": 0 }, { "w": 1, "x": 11, "y": 0 }, { "w": 1, "x": 12, "y": 0 }, { "w": 1, "x": 13, "y": 0 }, { "w": 1, "x": 14, "y": 0 }, { "w": 1, "x": 15.5, "y": 0 }, { "w": 1.5, "x": 0, "y": 1 }, { "w": 1, "x": 1.5, "y": 1 }, { "w": 1, "x": 2.5, "y": 1 }, { "w": 1, "x": 3.5, "y": 1 }, { "w": 1, "x": 4.5, "y": 1 }, { "w": 1, "x": 5.5, "y": 1 }, { "w": 1, "x": 6.5, "y": 1 }, { "w": 1, "x": 7.5, "y": 1 }, { "w": 1, "x": 8.5, "y": 1 }, { "w": 1, "x": 9.5, "y": 1 }, { "w": 1, "x": 10.5, "y": 1 }, { "w": 1, "x": 11.5, "y": 1 }, { "w": 1, "x": 12.5, "y": 1 }, { "w": 1.5, "x": 13.5, "y": 1 }, { "w": 1, "x": 15.5, "y": 1 }, { "w": 1.75, "x": 0, "y": 2 }, { "w": 1, "x": 1.75, "y": 2 }, { "w": 1, "x": 2.75, "y": 2 }, { "w": 1, "x": 3.75, "y": 2 }, { "w": 1, "x": 4.75, "y": 2 }, { "w": 1, "x": 5.75, "y": 2 }, { "w": 1, "x": 6.75, "y": 2 }, { "w": 1, "x": 7.75, "y": 2 }, { "w": 1, "x": 8.75, "y": 2 }, { "w": 1, "x": 9.75, "y": 2 }, { "w": 1, "x": 10.75, "y": 2 }, { "w": 1, "x": 11.75, "y": 2 }, { "w": 1, "x": 12.75, "y": 2 }, { "w": 1.25, "x": 13.75, "y": 2 }, { "w": 1.25, "x": 0, "y": 3 }, { "w": 1, "x": 1.25, "y": 3 }, { "w": 1, "x": 2.25, "y": 3 }, { "w": 1, "x": 3.25, "y": 3 }, { "w": 1, "x": 4.25, "y": 3 }, { "w": 1, "x": 5.25, "y": 3 }, { "w": 1, "x": 6.25, "y": 3 }, { "w": 1, "x": 7.25, "y": 3 }, { "w": 1, "x": 8.25, "y": 3 }, { "w": 1, "x": 9.25, "y": 3 }, { "w": 1, "x": 10.25, "y": 3 }, { "w": 1, "x": 11.25, "y": 3 }, { "w": 1, "x": 12.25, "y": 3 }, { "w": 1.25, "x": 13.25, "y": 3 }, { "w": 1, "x": 14.5, "y": 3 }, { "w": 1.25, "x": 0, "y": 4 }, { "w": 1, "x": 1.25, "y": 4 }, { "w": 1.25, "x": 2.25, "y": 4 }, { "w": 1.25, "x": 3.5, "y": 4 }, { "w": 2, "x": 4.75, "y": 4 }, { "w": 2, "x": 6.75, "y": 4 }, { "w": 1.25, "x": 8.75, "y": 4 }, { "w": 1.25, "x": 10, "y": 4 }, { "w": 1, "x": 11.25, "y": 4 }, { "w": 1.25, "x": 12.25, "y": 4 }, { "w": 1, "x": 13.5, "y": 4 }, { "w": 1, "x": 14.5, "y": 4 }, { "w": 1, "x": 15.5, "y": 4 } ]
      },
    }
  }
}
```

As you can see the payload describes all aspects of a keyboard necessary to create and generate a firmware. Each layer is a single list of QMK keycodes the same length as the keyboard's `LAYOUT` macro. If a keyboard supports mulitple `LAYOUT` macros you can specify which macro to use.

## Submitting a Compile Job

To compile your keymap into a firmware simply POST your JSON to the `/v1/compile` endpoint. In the following example we've placed the JSON payload into a file named `json_data`.

```
$ curl -H "Content-Type: application/json" -X POST -d "$(< json_data)" http://compile.qmk.fm/v1/compile
{
  "enqueued": true,
  "job_id": "ea1514b3-bdfc-4a7b-9b5c-08752684f7f6"
}
```

## Checking The Status

After submitting your keymap you can check the status using a simple HTTP GET call:

```
$ curl http://compile.qmk.fm/v1/compile/ea1514b3-bdfc-4a7b-9b5c-08752684f7f6
{
  "created_at": "Sat, 19 Aug 2017 21:39:12 GMT",
  "enqueued_at": "Sat, 19 Aug 2017 21:39:12 GMT",
  "id": "f5f9b992-73b4-479b-8236-df1deb37c163",
  "status": "running",
  "result": null
}
```

This shows us that the job has made it through the queue and is currently running. There are 5 possible statuses:

* **failed**: Something about the compiling service has broken.
* **finished**: The compilation is complete and you should check `result` to see the results.
* **queued**: The keymap is waiting for a compilation server to become available.
* **running**: The compilation is in progress and should be complete soon.
* **unknown**: A serious error has occurred and you should [file a bug](https://github.com/qmk/qmk_compiler_api/issues).

## Downloading The Results

When your job has completed and the compilation was successful you can download your new firmware. To download only the .hex file for flashing append "hex" to your URL:

```
$ curl -i http://compile.qmk.fm/v1/compile/9dbf56d1-9d6f-4d1a-a7e3-af1d6ecbdd65/hex
HTTP/1.0 200 OK
Content-Disposition: attachment; filename=clueboard_rev2_my_awesome_keymap.hex
Content-Length: 63558
Content-Type: application/octet-stream
Last-Modified: Sat, 19 Aug 2017 22:46:54 GMT
Cache-Control: public, max-age=43200
Expires: Sun, 20 Aug 2017 10:47:19 GMT
ETag: "1503182814.0-63558-190654682"
Date: Sat, 19 Aug 2017 22:47:19 GMT

:100000000C94BD050C9404060C9404060C94040690
:100010000C9404060C9404060C9404060C94040638
:100020000C9404060C9404060C94F7280C94CA292A
:100030000C9472200C9404060C9404060C94040690
*truncated*
```

If you'd like to download the source code as well as the hex you can append "source" instead:

```
$ curl http://compile.qmk.fm/v1/compile/9dbf56d1-9d6f-4d1a-a7e3-af1d6ecbdd65/source > qmk_firmware.zip
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 10.8M  100 10.8M    0     0  52.2M      0 --:--:-- --:--:-- --:--:-- 52.0M
$ file qmk_firmware.zip
qmk_firmware.zip: Zip archive data, at least v1.0 to extract
```
