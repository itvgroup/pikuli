# -*- coding: utf-8 -*-
from contextlib import contextmanager
from ctypes import windll
from enum import Enum

import win32api
import win32con

from ..helper_types import WindowsButtonCode


class WinVirtKeyCodes(int, Enum):
    """
    Virtual-key codes of some special keys.

    "MSDN: Virtual-Key Codes"
    https://docs.microsoft.com/en-us/windows/desktop/inputdev/virtual-key-codes
    """
    ALT        = win32con.VK_MENU
    CTRL       = win32con.VK_CONTROL
    SHIFT      = win32con.VK_SHIFT
    ENTER      = win32con.VK_RETURN
    ESC        = win32con.VK_ESCAPE
    TAB        = win32con.VK_TAB
    LEFT       = win32con.VK_LEFT
    UP         = win32con.VK_UP
    RIGHT      = win32con.VK_RIGHT
    DOWN       = win32con.VK_DOWN
    PAGE_UP    = win32con.VK_PRIOR
    PAGE_DOWN  = win32con.VK_NEXT
    HOME       = win32con.VK_HOME
    END        = win32con.VK_END
    BACKSPACE  = win32con.VK_BACK
    DELETE     = win32con.VK_DELETE
    SPACEBAR   = win32con.VK_SPACE
    F1         = win32con.VK_F1
    F2         = win32con.VK_F2
    F3         = win32con.VK_F3
    F4         = win32con.VK_F4
    F5         = win32con.VK_F5
    F6         = win32con.VK_F6
    F7         = win32con.VK_F7
    F8         = win32con.VK_F8
    F9         = win32con.VK_F9
    F10        = win32con.VK_F10
    F11        = win32con.VK_F11
    F12        = win32con.VK_F12


class WinButtonCode(WindowsButtonCode, Enum):
    LEFT   = (win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP)
    RIGHT  = (win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP)
    MIDDLE = (win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP)


class WinScrollDirection(int, Enum):
    UP = 1
    DOWN = -1


class InputMixin(object):

    @staticmethod
    @contextmanager
    def block_input():
        windll.user32.BlockInput(True)
        yield
        windll.user32.BlockInput(False)


class WinKeyboardMixin(InputMixin):

    @classmethod
    def _char_to_keycode(cls, char):
        """
        Returns a Virtual-key Code of the character `char`.
        """
        vk_code = win32api.VkKeyScan(char)
        need_shift_key = bool(vk_code & 0x100)
        return vk_code, need_shift_key

    @classmethod
    def _do_press_key(cls, key_code):
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_EXTENDEDKEY, 0)  # win32con.KEYEVENTF_EXTENDEDKEY   # TODO: is scan code needed?

    @classmethod
    def _do_release_key(cls, key_code):
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)  # win32con.KEYEVENTF_EXTENDEDKEY


class WinMouseMixin(InputMixin):

    @classmethod
    def _do_press_button(cls, btn_code):
        return win32api.mouse_event(btn_code.event_down, 0, 0, 0, 0)

    @classmethod
    def _do_release_button(cls, btn_code):
        return win32api.mouse_event(btn_code.event_up, 0, 0, 0, 0)

    @classmethod
    def _set_mouse_pos(cls, x, y):
        """ """
        win32api.SetCursorPos((x, y))

    @classmethod
    def _get_mouse_pos(cls):
        """
        :return: :class:`tuple` of `(x, y)`
        """
        return win32api.GetCursorPos()

    @classmethod
    def _do_scroll(cls, direction, step=1):
        x, y = cls._get_mouse_pos()
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, x, y, int(direction) * step, 0)
