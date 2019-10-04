# QMK Keymap Compiler API

This page describes the API for interacting with QMK Compiler. If you are an application developer you can use this API to compile firmware for any [QMK](https://qmk.fm) Keyboard.

## Overview

This service is an asynchronous API for compiling custom keymaps. You POST some JSON to the API, periodically check the status, and when your firmware has finished compiling you can download the resulting firmware and (if desired) source code for that firmware.

#### Example JSON Payload:

```json
{
  "keyboard": "clueboard/66/rev2",
  "keymap": "my_awesome_keymap",
  "layout": "KEYMAP",
  "layers": [
    ["KC_GRV","KC_1","KC_2","KC_3","KC_4","KC_5","KC_6","KC_7","KC_8","KC_9","KC_0","KC_MINS","KC_EQL","KC_GRV","KC_BSPC","KC_PGUP","KC_TAB","KC_Q","KC_W","KC_E","KC_R","KC_T","KC_Y","KC_U","KC_I","KC_O","KC_P","KC_LBRC","KC_RBRC","KC_BSLS","KC_PGDN","KC_CAPS","KC_A","KC_S","KC_D","KC_F","KC_G","KC_H","KC_J","KC_K","KC_L","KC_SCLN","KC_QUOT","KC_NUHS","KC_ENT","KC_LSFT","KC_NUBS","KC_Z","KC_X","KC_C","KC_V","KC_B","KC_N","KC_M","KC_COMM","KC_DOT","KC_SLSH","KC_RO","KC_RSFT","KC_UP","KC_LCTL","KC_LGUI","KC_LALT","KC_MHEN","KC_SPC","KC_SPC","KC_HENK","KC_RALT","KC_RCTL","MO(1)","KC_LEFT","KC_DOWN","KC_RIGHT"],
    ["KC_ESC","KC_F1","KC_F2","KC_F3","KC_F4","KC_F5","KC_F6","KC_F7","KC_F8","KC_F9","KC_F10","KC_F11","KC_F12","KC_TRNS","KC_DEL","BL_STEP","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","_______","KC_TRNS","KC_PSCR","KC_SLCK","KC_PAUS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","MO(2)","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_PGUP","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","MO(1)","KC_LEFT","KC_PGDN","KC_RGHT"],
    ["KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","RESET","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","MO(2)","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","KC_TRNS","MO(1)","KC_TRNS","KC_TRNS","KC_TRNS"]
  ]
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
