# -*- coding: utf-8 -*-

from Xlib.display import Display
# from Xlib.protocol.event import KeyPress, KeyRelease


class X11Base(object):

    _display = Display()
    _root_window = _display.screen().root

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

class X11MouseMixin(X11Base):

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
