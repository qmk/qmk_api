# Keyboard API

The QMK API supplies extensive information about keyboards and keymaps in the master branch of [qmk_firmware](https://github.com/qmk/qmk_firmware). Configurator frontends can use this information to progmatically build configuration interfaces for any QMK supported keyboard.

## Versions

Currently there is only one version of the QMK API, and this is the base url:

> https://api.qmk.fm/v1

Additive changes to this standard will be added to the current version. The version number will be incremented if breaking changes need to happen.

## Converters

API endpoints are provided for converting between keyboard-layout-editor.com Raw Code and QMK's info.json format. 

### KLE to info.json

    Method: POST
    URL: https://api.qmk.fm/v1/converters/kle
    Payload: gist id or KLE raw code

You can use this endpoint to convert from keyboard-layout-editor.com to info.json. The data payload takes one of two forms, depending on whether you supply a gist ID or the raw code.

#### Gist ID

If you have a gist ID to pass in your data payload should look like this:

    {"id": "gist_identifier_hash"}
    
#### KLE Raw Code

If you have Raw Code to pass in your data payload should look like this:

    {
        "raw": [
            ["1", "2", "3"],
            ["q", "w", "e"],
        ]
    }

## Keyboards

The QMK API provides a list of and metadata about all keyboards supported by QMK.

### Keyboard List

    https://api.qmk.fm/v1/keyboards
    
You can get a list of all keyboards supported by QMK at this URL.

### Keyboard Metadata

To get metadata about specific keyboards by appending them to the URL. For example, to see information about Clueboard 60%:

    https://api.qmk.fm/v1/keyboards/clueboard/60
    
You can fetch multiple keyboards by separating them with a comma:

    http://api.qmk.fm/v1/keyboards/ergodox_ez,ergodox_infinity
    
There is also a special `all` keyword that fetches metadata for every keyboard supported by QMK:

    https://api.qmk.fm/v1/keyboards/all
    
### Keyboard Documentation

You can fetch the `readme.md` file for a particular keyboard by adding `/readme` to the end of the URL:

    https://api.qmk.fm/v1/keyboards/planck/readme
    
### Keymaps

Every keymap contributed to QMK is available through the API. A list of keymaps is available in the keyboard metadata. To fetch a particular keymap you can hit the keymap URL:

    https://api.qmk.fm/v1/keyboards/<keyboard>/keymaps/<keymap>
    
You can also fetch the keymap's readme file by appending `readme` to that URL:

    https://api.qmk.fm/v1/keyboards/<keyboard>/keymaps/<keymap>/readme
