# -*- coding: utf-8 -*-

from enum import Enum, EnumMeta

from .helper_types import Flag, NullPrefixStr
from .platform_init import KeyCode, ScrollDirection


class KeyMeta(EnumMeta):
    def __new__(mcls, name, bases, dct):
        dct.update({e.name: e.value for e in list(KeyCode)})
        return super(KeyMeta, mcls).__new__(mcls, name, bases, dct)


class KeyModifier(Flag, Enum):
    '''
    Битовые маски модификаторов. С их помощью будет парсится аргумент modifiers функции type_text().
    '''
    ALT   = 0x01
    CTRL  = 0x02
    SHIFT = 0x04

    @classmethod
    def int2flags(cls, val):
        return [e for e in list(cls) if e.is_set_in(val)]


class Key(NullPrefixStr, Enum):
    '''
    Пары '\x00' и кода специальных клавиш. Пары хранятся как строки из (два символа), позволяет лего
    добавлять их к строкам в коде. К примеру:
        type_text("some text" + Key.ENTER)

    Код клавишы зависит от OS. Для Windows это Virtual-key Code, а в Linux -- коды evdev.

    Ноль-символ, предваряющий код клавиши, сигнализирует о том, что после него идет не печатный
    литера, а OS-зависимый код спецаильного символа.
    '''
    __metaclass__ = KeyMeta
