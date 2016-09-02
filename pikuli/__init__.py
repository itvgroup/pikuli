# -*- coding: utf-8 -*-

''' Пока что этот модуль -- прослойка для Sikuli.
    В перспективе мы сможем отказаться от Sikuli, дописывая только этот модуль

Doc pywin32:
    http://timgolden.me.uk/pywin32-docs/modules.html

Особенности использования памяти:
    -- При создании объекта Pattern, от сделает
       self._cv2_pattern = cv2.imread(self.getFilename())

'''

import os
import logging
import sys

from ._functions import *
from ._exceptions import *
from ._SettingsClass import *

from .Region import Region
from .Match import Match
from .Screen import Screen
from .Location import Location
from .Pattern import Pattern


Settings = SettingsClass()
logger = logging.getLogger('axxon.pikuli')

try:
    Settings.addImagePath(
        os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__)))
except Exception as e:
    logger.error('Problem with addImagePath: {}'.format(e))

__all__ = [
    'Settings',
    'Region',
    'Screen',
    'Match',
    'Location',
    'Pattern',
]


class LogRecord(str):
    def __new__(cls, *chunks):
        sep = ' '
        value = sep.join(str(chunk) for chunk in chunks)
        return str.__new__(cls, value)


class File(object):
    def __init__(self, filename):
        self.abspath = os.path.abspath(filename)
