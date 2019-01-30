# -*- coding: utf-8 -*-

from enum import Enum, EnumMeta

from .helper_types import NullPrefixStr
from .platform_init import KeyCode, ScrollDirection


class _KeyMeta(EnumMeta):
    def __new__(mcls, name, bases, dct):
        dct.update({e.name: e.value for e in list(KeyCode)})
        return super(_KeyMeta, mcls).__new__(mcls, name, bases, dct)


class Key(NullPrefixStr, Enum):
    '''
    Пары '\x00' и кода специальных клавиш. Пары хранятся как строки из (два символа), позволяет лего
    добавлять их к строкам в коде. К примеру:
        type_text("some text" + Key.ENTER)

    Код клавиши зависит от OS. Для Windows это Virtual-key Code, а в Linux -- коды evdev.

    Ноль-символ, предваряющий код клавиши, сигнализирует о том, что после него идет не печатная
    литера, а OS-зависимый код спецаильного символа.
    '''

    __metaclass__ = _KeyMeta

    @property
    def key_code(self):
        key_code_str = NullPrefixStr.drop_nullprefix(self.value)
        return ord(key_code_str)


class KeyModifier(str, Enum):
    '''
    Аргумент modifiers функции type_text().
    '''
    ALT   = Key.ALT.value
    CTRL  = Key.CTRL.value
    SHIFT = Key.SHIFT.value

    @classmethod
    def _str_to_key_codes(cls, s):
        out = []
        for item in list(str2items(s)):
            assert (item in Key) and KeyModifier(item)
            out.append(item.key_code)
        return out


def str2items(s):
    s = unicode(s)
    out = []

    idxes = iter(xrange(len(s)))
    for i in idxes:
        char = s[i]
        try:
            char_next = s[i+1]
            special_key = Key(char + char_next)
        except:
            out.append(char)
        else:
            idxes.next()
            out.append(special_key)

    return out
