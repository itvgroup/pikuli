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

try:
    Settings.addImagePath(
        os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__)))
except Exception as e:
    logging.getLogger('axxon.pikuli').error(
        'Problem with addImagePath: {}'.format(e))

__all__ = [
    'Settings',
    'Region',
    'Screen',
    'Match',
    'Location',
    'Pattern',
]
