# -*- coding: utf-8 -*-

"""
TODO: see
    https://github.com/moses-palmer/pynput
    https://github.com/asweigart/pyautogui
"""
import traceback

from pikuli._helpers import NotImplemetedDummyFactory

try:
    from .input_emulator import InputEmulator
    from .keys import Key, KeyModifier, ScrollDirection
    from .platform_init import Clipboard, ButtonCode

except Exception as ex:
    err_msg = traceback.format_exc()
    (
        InputEmulator,
        Key,
        KeyModifier,
        ScrollDirection,
        Clipboard,
        ButtonCode
    ) = NotImplemetedDummyFactory.make_classes(
        [
            'InputEmulator',
            'Key',
            'KeyModifier',
            'ScrollDirection',
            'Clipboard',
            'ButtonCode',
        ],
        reason=err_msg)

