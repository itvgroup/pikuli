# -*- coding: utf-8 -*-

''' Пока что этот модуль -- прослойка для Sikuli. В перспективе мы сможем отказаться от Sikuli, дописывая только этот модуль

Doc pywin32:
    http://timgolden.me.uk/pywin32-docs/modules.html

Особенности использования памяти:
    -- При создании объекта Pattern, от сделает self._cv2_pattern = cv2.imread(self.getFilename())

'''

from ._functions import *
from ._exceptions import *
from ._SettingsClass import *
# from ._LoggerClass import *

from .Region import Region
from .Match import Match
from .Screen import Screen
from .Location import Location
from .Pattern import Pattern


# # Класс логгера:
# Logger = LoggerClass()

# Создадим экземпляр класса Settings(он будет создаваться только один раз, даже если импорт модуля происходит мого раз в разных местах)
# и добавим путь к тому фйлу, из которого импортировали настоящий модуль:
Settings = SettingsClass()
# Settings.addImagePath(os.getcwd()) -- надо ли так?
try:
    Settings.addImagePath(os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__)))
except:
    p2c('[warn] err in Settings.addImagePath(os.path.dirname(os.path.abspath(sys.modules[\'__main__\'].__file__)))')

__all__ = ['Settings',
           'Region',
           'Screen',
           'Match',
           'Location',
           'Pattern']

