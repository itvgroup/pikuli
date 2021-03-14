# -*- coding: utf-8 -*-

import os
from collections import namedtuple
from contextlib import contextmanager

from pikuli import logger
from pikuli._helpers import NotImplemetedDummyFactory


Method = namedtuple('Method', [
    'KeyCode',
    'ButtonCode',
    'ScrollDirection',
    'OsKeyboardMixin',
    'OsMouseMixin',
    'Clipboard'
])


class EmulatorMethod(object):
    """
    One can use this class to switch input emulation method in two ways: permanent or temporary.

    Permanent selecetion::

        EmulatorMethod.set_method('...')

    Temporary selection::

        with EmulatorMethod('...'):
            ...
    """

    _current_method = None
    _collection = {}

    @contextmanager
    def __new__(self, temp_method):
        bckp_method = self.get_method()
        self.set_method(temp_method)
        yield
        self.set_method(bckp_method)

    @classmethod
    def get_method(cls):
        return cls._current_method

    @classmethod
    def set_method(cls, new_method):
        global KeyCode  # :class:`KeyCode` is the internal class. The public one is :class:`Key`, builded in the `keys.py`.
        global ButtonCode
        global ScrollDirection
        global OsKeyboardMixin
        global OsMouseMixin
        global Clipboard

        KeyCode, ButtonCode, ScrollDirection, OsKeyboardMixin, OsMouseMixin, Clipboard = cls._collection[new_method]
        cls._current_method = new_method

if os.name == 'nt':
    from .windows.input_emulator import WinVirtKeyCodes
    from .windows.input_emulator import WinButtonCode
    from .windows.input_emulator import WinScrollDirection
    from .windows.input_emulator import WinKeyboardMixin
    from .windows.input_emulator import WinMouseMixin
    from .windows.clipboard import WinClipboard

    EmulatorMethod._collection['win'] = Method(
        WinVirtKeyCodes, WinButtonCode, WinScrollDirection, WinKeyboardMixin, WinMouseMixin, WinClipboard)

    EmulatorMethod.set_method('win')

elif os.name == 'posix':
    from .linux_evdev.input_emulator import EvdevKeyCodes
    from .linux_evdev.input_emulator import EvdevButtonCode
    from .linux_evdev.input_emulator import EvdevScrollDirection
    from .linux_evdev.input_emulator import EvdevKeyboardMixin
    from .linux_evdev.input_emulator import EvdevMouseMixin

    from .linux_x11.input_emulator import X11MouseMixin

    from .linux_gtk3.input_emulator import GtkKeyboardMixin
    from .linux_gtk3.clipboard import GtkClipboard

    class EvdevX11MouseMixin(EvdevMouseMixin, X11MouseMixin):
        pass

    class EmulatorMethodLazyGetter(object):
        def __str__(self):
            return str(EmulatorMethod.get_method())
        def __repr__(self):
            return repr(EmulatorMethod.get_method())
    NotImplemetedDummy = NotImplemetedDummyFactory.make_class(
        'NotImplemetedDummy',
        msg='InputEmulator attribute {attr!r} is not available while input method is {input_methods!s}',
        input_methods=EmulatorMethodLazyGetter())

    EmulatorMethod._collection['evdev'] = Method(
        EvdevKeyCodes, EvdevButtonCode, EvdevScrollDirection, EvdevKeyboardMixin, EvdevMouseMixin, NotImplemetedDummy)

    EmulatorMethod._collection['x11'] = Method(
        NotImplemetedDummy, NotImplemetedDummy, NotImplemetedDummy, NotImplemetedDummy, X11MouseMixin, NotImplemetedDummy)

    EmulatorMethod._collection['gtk3'] = Method(
        NotImplemetedDummy, NotImplemetedDummy, NotImplemetedDummy, GtkKeyboardMixin, NotImplemetedDummy, GtkClipboard)

    EmulatorMethod._collection['evdev+x11+gtk3'] = Method(
        EvdevKeyCodes, EvdevButtonCode, EvdevScrollDirection, GtkKeyboardMixin, EvdevX11MouseMixin, GtkClipboard)

    EmulatorMethod.set_method('evdev+x11+gtk3')

else:
    raise Exception('Not supported: os.name = {}'.format(os.name))
