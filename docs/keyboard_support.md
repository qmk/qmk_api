# QMK Compiler Keyboard Suppport

By default the template that QMK Compiler has is very limited. You can only specify a keymap and can not reference macros or custom keys. QMK Compiler supports custom templates so your compiled keymaps can be more featureful.

## Default Template

This is the default template that QMK Compiler uses:

```
#include QMK_KEYBOARD_H

// Helpful defines
#define _______ KC_TRNS

const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {
__KEYMAP_GOES_HERE__
};
```

## Supplying Your Own Template

If you'd like to supply a custom template you can do so. Create a directory named `templates` inside your keyboard's directory, next to `keymaps`. If QMK Compiler finds a file named `keymap.c` it will use that as your keyboard's template. Make sure that you have the string `__KEYMAP_GOES_HERE__` inside your template so QMK Compiler knows where to insert the keymap.
