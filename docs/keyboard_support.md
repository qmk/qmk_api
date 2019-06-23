# QMK Compiler Keyboard Suppport

[[toc]]

By default the template that QMK Compiler has is very limited. You can only specify a keymap and can not reference macros or custom keys. QMK Compiler lets you specify information about your keyboard so that configurator apps can make use of them.

## Keyboard Metadata

To aid Web and GUI programs that wish to use this API we are publishing metadata about keyboards. You can use this metadata to get information about the keyboard like Manufacturer, Product and Vendor ID's, Processor, and more. This data is populated from the [qmk_firmware](https://github.com/qmk/qmk_firmware) repository.

### Available Metadata

## Keymap Templates

QMK Compiler builds a keymap based on the layout you submit in your JSON payload. To do it makes use of a template file to generate that keymap.

### Default Template

This is the default template that QMK Compiler uses:

```
#include QMK_KEYBOARD_H

// Helpful defines
#define _______ KC_TRNS

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
__KEYMAP_GOES_HERE__
};
```

### Supplying Your Own Template

If you'd like to supply a custom template you can do so. Create a directory named `templates` inside your keyboard's directory, next to `keymaps`. If QMK Compiler finds a file named `keymap.c` it will use that as your keyboard's template. Make sure that you have the string `__KEYMAP_GOES_HERE__` inside your template so QMK Compiler knows where to insert the keymap.
