# -*- coding: utf-8 -*-

import gi
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk

from ..linux_evdev.input_emulator import EvdevKeyboardMixin


class GtkKeyboardMixin(EvdevKeyboardMixin):
    """
    NOT WORKS AT ALL YET!
    """

    @classmethod
    def _char_to_keycode(cls, char):
        """
        Returns an ``evdev`` key code of the unicode printable character `char`.
        """
        charcode = ord(str(char))
        x11_keysym = Gdk.unicode_to_keyval(charcode)  # X11 KeySym
        x11_keycode = cls._display.keysym_to_keycode(x11_keysym)  # X11 KeyCode

        # Got "shift" status:
        code_syms = cls._display._keymap_codes[x11_keycode]  # Faster than `keycode_to_keysym()`. TODO: Use `XGetKeyboardMapping`?
        idx = code_syms.index(x11_keysym)
        is_shift = bool(idx % 2)  # WARNING: Not exactly like doc of :func:`Xlib.display.Display.keycode_to_keysym` says.

        # X11 KeyCode to evdev key code:
        if x11_keysym == 0xff0d:  # Return
            ascii = 0x0201
        elif x11_keysym == 0xff09:  # Tab
            ascii = 0x0009
        elif x11_keysym == 0xff08:  # BackSpace
            ascii = 0x0008
        elif idx not in (0, 1):
            raise NotImplemented()
            '''
            .... Need to switch to another layout!

            TODO: try to use this (not works yet)

            print Gdk.test_simulate_button(w, 100, 100, 3, 0, Gdk.EventType.BUTTON_PRESS)
            time.sleep(0.5)
            print Gdk.test_simulate_button(w, 100, 100, 3, 0, Gdk.EventType.BUTTON_RELEASE)

            charcode = ord(u't')
            keyval = Gdk.unicode_to_keyval(charcode)
            print charcode, keyval
            print Gdk.test_simulate_key(w, 300, 300, keyval, 0, Gdk.EventType.KEY_PRESS)
            print Gdk.test_simulate_key(w, 300, 300, keyval, 0, Gdk.EventType.KEY_RELEASE)

            '''
        else:
            ascii = x11_keysym

        evdev_code, _ = cls._keycode_and_shift_by_ascii[ascii]

        return evdev_code, is_shift

