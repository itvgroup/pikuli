# -*- coding: utf-8 -*-

from collections import namedtuple


class Flag(int):

    def is_set_in(self, val):
        return bool(self & val)


class NullPrefixStr(str):

    def __new__(cls, val):
        return super(NullPrefixStr, cls).__new__(cls, '\x00' + str(val))


WindowsButtonCode = namedtuple('WindowsButtonCode', ['event_down', 'event_up'])
