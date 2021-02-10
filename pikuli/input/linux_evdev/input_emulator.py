# -*- coding: utf-8 -*-

import os
from contextlib import contextmanager

from enum import Enum
from evdev import ecodes
from evdev.uinput import UInput


class EvdevKeyCodes(int, Enum):
    """
    `evdev` key codes (see `linux/include/uapi/linux/input-event-codes.h`)
    """
    ALT        = ecodes.KEY_LEFTALT
    CTRL       = ecodes.KEY_LEFTCTRL
    SHIFT      = ecodes.KEY_LEFTSHIFT
    ENTER      = ecodes.KEY_ENTER
    ESC        = ecodes.KEY_ESC
    TAB        = ecodes.KEY_TAB
    LEFT       = ecodes.KEY_LEFT
    UP         = ecodes.KEY_UP
    RIGHT      = ecodes.KEY_RIGHT
    DOWN       = ecodes.KEY_DOWN
    PAGE_UP    = ecodes.KEY_PAGEUP
    PAGE_DOWN  = ecodes.KEY_PAGEDOWN
    HOME       = ecodes.KEY_HOME
    END        = ecodes.KEY_END
    BACKSPACE  = ecodes.KEY_BACKSPACE
    DELETE     = ecodes.KEY_DELETE
    SPACEBAR   = ecodes.KEY_SPACE
    F1         = ecodes.KEY_F1
    F2         = ecodes.KEY_F2
    F3         = ecodes.KEY_F3
    F4         = ecodes.KEY_F4
    F5         = ecodes.KEY_F5
    F6         = ecodes.KEY_F6
    F7         = ecodes.KEY_F7
    F8         = ecodes.KEY_F8
    F9         = ecodes.KEY_F9
    F10        = ecodes.KEY_F10
    F11        = ecodes.KEY_F11
    F12        = ecodes.KEY_F12


class EvdevButtonCode(int, Enum):
    LEFT   = ecodes.BTN_LEFT
    RIGHT  = ecodes.BTN_RIGHT
    MIDDLE = ecodes.BTN_MIDDLE


class EvdevScrollDirection(int, Enum):
    UP = 1
    DOWN = -1


def _TEMP_parse_dumpkeys_output():
    """
    TODO: use bindings to `keymap`
    """

    def collect_lines(file_name, startswith):
        base_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(base_path, file_name)) as f:
            for l in iter(f.readline, ''):
                if l.startswith(startswith):
                    yield l

    charnames_by_ascii = {}  # It seems, that ASCII....
    ascii_by_charnames = {}
    for l in collect_lines('dumpkeys_l.txt', '0x'):
        hex_ascii, charname = l.split()
        ascii = int(hex_ascii, 16)
        if ascii <= 127:
            charnames_by_ascii[ascii] = charname
            ascii_by_charnames[charname] = ascii

    keycode_and_shift_by_ascii = {}
    for l in collect_lines('dumpkeys_f.txt', 'keycode '):
        splitted = l.split()
        keycode = int(splitted[1])
        charname_normal = splitted[3].lstrip('+')
        charname_shifted = splitted[4].lstrip('+')

        try:
            ascii_normal = ascii_by_charnames[charname_normal]
            ascii_shifted = ascii_by_charnames[charname_shifted]
            keycode_and_shift_by_ascii[ascii_normal] = (keycode, False)
            keycode_and_shift_by_ascii[ascii_shifted] = (keycode, True)
        except:
            pass

    return keycode_and_shift_by_ascii


class InputMixin(object):

    @staticmethod
    @contextmanager
    def block_input():
        yield


class EvdevBase(object):

    _uinput_dev = UInput(
        events={
            ecodes.EV_KEY: ecodes.keys.keys(),
            ecodes.EV_REL: [ecodes.REL_WHEEL]
        },
        name='pikuli-evdev-uinput')


class EvdevKeyboardMixin(EvdevBase, InputMixin):

    _keycode_and_shift_by_ascii = _TEMP_parse_dumpkeys_output()

    @classmethod
    def _char_to_keycode(cls, char):
        """
        Returns a `evdev` key code of the character `char`. Supports only Latin characters.

        TODO: Investigate `dumpkeys` and keymap at all.
              https://wiki.archlinux.org/index.php/Linux_console_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)/Keyboard_configuration_(%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9)
              https://kernel.googlesource.com/pub/scm/linux/kernel/git/legion/kbd/+/1.10/src/showkey.c
              https://kernel.googlesource.com/pub/scm/linux/kernel/git/legion/kbd/+/1.10/src/dumpkeys.c
              https://www.systutorials.com/docs/linux/man/1-dumpkeys/
              https://www.systutorials.com/docs/linux/man/5-keymaps/
        TEMP: Hardcoded map for Latin symbols only. Do it by use of OS system calls.
        """
        return cls._keycode_and_shift_by_ascii[ord(char)]

    @classmethod
    def _do_press_key(cls, key_code):
        cls._uinput_dev.write(ecodes.EV_KEY, key_code, 1)
        cls._uinput_dev.syn()

    @classmethod
    def _do_release_key(cls, key_code):
        cls._uinput_dev.write(ecodes.EV_KEY, key_code, 0)
        cls._uinput_dev.syn()


class EvdevMouseMixin(EvdevBase, InputMixin):

    @classmethod
    def _do_press_button(cls, btn_code):
        cls._uinput_dev.write(ecodes.EV_KEY, btn_code, 1)
        cls._uinput_dev.syn()

    @classmethod
    def _do_release_button(cls, btn_code):
        cls._uinput_dev.write(ecodes.EV_KEY, btn_code, 0)
        cls._uinput_dev.syn()

    @classmethod
    def _do_scroll(cls, direction, step=1):
        cls._uinput_dev.write(ecodes.EV_REL, ecodes.REL_WHEEL, direction * step)
        cls._uinput_dev.syn()

