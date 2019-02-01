# -*- coding: utf-8 -*-

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

from pikuli import logger


class GtkClipboard(object):

    _clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

    @classmethod
    def get_text_from_clipboard(cls, p2c_notif=True):
        text = cls._clipboard.wait_for_text()
        logger.info('get_text_from_clipboard: text = {!r}'.format(text))
        return text

    @classmethod
    def set_text_to_clipboard(cls, data):
        logger.debug('set_text_to_clipboard: data = {d!r} ({d!s})'.format(d=data))
        cls._clipboard.set_text(str(data), -1)
        cls._clipboard.store()

