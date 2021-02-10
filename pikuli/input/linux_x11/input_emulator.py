# -*- coding: utf-8 -*-

from Xlib.display import Display
# from Xlib.protocol.event import KeyPress, KeyRelease
from decorator import contextmanager

from ..helper_types import _HookedClassInit

class X11Base(_HookedClassInit):

    @classmethod
    def __hooked_class_init(cls):
        cls._display = Display()
        cls._root_window = cls._display.screen().root


'''
class X11KeyboardMixin(X11Base):
    """
    NOT WORKS YET!

    see https://github.com/python-xlib/python-xlib/blob/master/Xlib/protocol/event.py
    """

    @classmethod
    def _do_press_key(cls, key_code):
        """ `key_code` is ... """
        active_windows = cls._display.get_input_focus().focus
        event = KeyPress(
        )
        _display.send_event(active_windows, event, )

    @classmethod
    def _do_release_key(cls, key_code):
        """ `key_code` is ... """
'''


class InputMixin(object):

    @staticmethod
    @contextmanager
    def block_input():
        yield


class X11MouseMixin(X11Base, InputMixin):

    __hooked_class_init_overriding = {
        X11Base: [
            '_set_mouse_pos',
            '_get_mouse_pos'
        ]
    }

    @classmethod
    def _set_mouse_pos(cls, x, y):
        cls._root_window.warp_pointer(x, y)
        cls._display.sync()

    @classmethod
    def _get_mouse_pos(cls):
        """
        :return: :class:`tuple` of `(x, y)`
        """
        pos = cls._root_window.query_pointer()
        return pos.root_x, pos.root_y
