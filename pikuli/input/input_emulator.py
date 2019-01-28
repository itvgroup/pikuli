# -*- coding: utf-8 -*-

import string
import time
from contextlib import contextmanager

from pikuli import logger

from .constants import (
    DELAY_KBD_KEY_PRESS, DELAY_KBD_KEY_RELEASE,
    DELAY_MOUSE_BTN_PRESS, DELAY_MOUSE_BTN_RELEASE,
    DELAY_MOUSE_CLICK, DELAY_MOUSE_DOUBLE_CLICK, DELAY_MOUSE_AFTER_ANY_CLICK,
    DELAY_MOUSE_SET_POS, DELAY_MOUSE_SCROLL
)
from .keys import str2items, Key
from .platform_init import ButtonCode, KeyCode, OsKeyboardMixin, OsMouseMixin


class KeyboardMixin(object):

    #_PrintableChars = set(string.printable) - set(????)
    # TODO: Latin and Cyrillic only yet.
    _PrintableChars = (
        set(u"0123456789!\"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n\r") |
        set(u"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") |
        set(u"абвгдеёжзийклмнопрстуфхцчщъьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧЩЪЬЭЮЯ №")
    )

    @classmethod
    def type_text(cls, s, modifiers=None, p2c_notif=True):
        """
        Особенности:
            -- Если установлены modifiers, то не будет различия между строчными и загалавными буквами.
               Т.е., будет если в строке "s" есть заглавные буквы, то Shift нажиматься не будет.
        """
        # https://mail.python.org/pipermail/python-win32/2013-July/012862.html
        # https://msdn.microsoft.com/ru-ru/library/windows/desktop/ms646304(v=vs.85).aspx ("MSDN: keybd_event function")
        # http://stackoverflow.com/questions/4790268/how-to-generate-keystroke-combination-in-win32-api
        # http://stackoverflow.com/questions/11906925/python-simulate-keydown
        # https://ru.wikipedia.org/wiki/Скан-код
        # http://stackoverflow.com/questions/21197257/keybd-event-keyeventf-extendedkey-explanation-required

        @contextmanager
        def _press_shift_if_necessary(char_need_shift_key):
            if char_need_shift_key and (not modifiers):
                cls.press_key(KeyCode.SHIFT)
                yield
                cls.release_key(KeyCode.SHIFT)
            else:
                yield

        cls.press_modifiers(modifiers)

        for item in str2items(s):
            try:
                key_code, need_shift = str_item_to_keycode(item)
            except Exception as ex:
                logger.exception(ex, 'Error dealing with symbol {!r} in string {!r}.'.format(item, s))
                raise
            with _press_shift_if_necessary(need_shift):
                cls.type_key(key_code)

        cls.release_modifiers(modifiers)

        if p2c_notif:
            logger.info('pikuli._functions.type_text(): {!r} '
                        'was typed; modifiers={!r}'.format(s, modifiers))

    @classmethod
    def str_item_to_keycode(cls, item):
        if item is Key:
            return (item.key_code, False)
        else:
            assert item in cls._PrintableChar, 'PrintableChars={!r}; item={!r}'.format(cls._PrintableChar, item)
            return cls._char_to_keycode(item)

    @classmethod
    def type_key(cls, key_code):
        cls.press_key(key_code)
        cls.release_key(key_code)

    @classmethod
    def press_modifiers(cls, modifiers):
        cls._do_modifier_keys_action(modifiers, cls.press_key)

    @classmethod
    def release_modifiers(cls, modifiers):
        cls._do_modifier_keys_action(modifiers, cls.release_key)

    @classmethod
    def press_key(cls, key_code):
        cls._do_press_key(key_code)
        time.sleep(DELAY_KBD_KEY_PRESS)

    @classmethod
    def release_key(cls, key_code):
        cls._do_release_key(key_code)
        time.sleep(DELAY_KBD_KEY_RELEASE)

    @classmethod
    def _do_modifier_keys_action(cls, modifiers, action):
        for modif_key_code in KeyModifier._str_to_key_codes(modifiers):
            action(modif_key_code)


class MouseMixin(object):

    @classmethod
    def left_click(cls):
        cls.click(ButtonCode.LEFT)

    @classmethod
    def right_click(cls):
        cls.click(ButtonCode.RIGHT)

    @classmethod
    def left_dbl_click(cls):
        cls.double_click(ButtonCode.LEFT)

    @classmethod
    def click(cls, btn_code):
        cls._click_with_no_after_sleep(btn_code)
        time.sleep(DELAY_MOUSE_AFTER_ANY_CLICK)

    @classmethod
    def double_click(cls, btn_code):
        cls._click_with_no_after_sleep(btn_code)
        time.sleep(DELAY_MOUSE_DOUBLE_CLICK)
        cls._click_with_no_after_sleep(btn_code)
        time.sleep(DELAY_MOUSE_AFTER_ANY_CLICK)

    @classmethod
    def _click_with_no_after_sleep(cls, btn_code):
        cls._do_press_button(btn_code)
        time.sleep(DELAY_MOUSE_CLICK)
        cls._do_release_button(btn_code)

    @classmethod
    def press_button(cls, key_code):
        cls._do_press_button(key_code)
        time.sleep(DELAY_MOUSE_BTN_PRESS)

    @classmethod
    def release_button(cls, key_code):
        cls._do_release_key(key_code)
        time.sleep(DELAY_MOUSE_BTN_RELEASE)

    @classmethod
    def set_mouse_pos(cls, x, y):
        cls._set_mouse_pos(x, y)
        time.sleep(DELAY_MOUSE_SET_POS)

    @classmethod
    def get_mouse_pos(cls):
        return cls._get_mouse_pos()

    @classmethod
    def scroll(cls, direction, count=1, step=1):
        for _ in range(0, count):
            cls._do_scroll(direction, step=step)
            time.sleep(DELAY_MOUSE_SCROLL)


class InputEmulator(
    KeyboardMixin, MouseMixin,
    OsKeyboardMixin, OsMouseMixin):
    pass
