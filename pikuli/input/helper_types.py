# -*- coding: utf-8 -*-

from collections import namedtuple


class NullPrefixStr(str):

    def __new__(cls, val):
        return super(NullPrefixStr, cls).__new__(cls, '\x00' + str(val))

    @classmethod
    def is_nullprefix(cls, s):
        return s[0] == '\x00'

    @classmethod
    def drop_nullprefix(cls, s):
        assert cls.is_nullprefix(s)
        return s[1:]


WindowsButtonCode = namedtuple('WindowsButtonCode', ['event_down', 'event_up'])
