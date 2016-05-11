# -*- coding: utf-8 -*-

import os
# import sys

# from _functions import p2c


class SettingsClass(object):

    __def_IMG_ADDITION_PATH = []  # Пути, кроме текущего и мб еще какого-то подобного
    __def_MinSimilarity = 0.995  # Почти устойчиво с 0.995, но однажны не нашел узелок для контура. 0.700 -- будет найдено в каждом пикселе (порог надо поднимать выше).
    __def_FindFailedDir = os.path.join(os.environ['TEMP'], 'find_failed')

    def __init__(self):
        defvals = self.__get_default_values()
        for k in defvals:
            setattr(self, k, defvals[k])

    def __get_default_values(self):
        defvals = {}
        for attr in dir(self):
            if '_SettingsClass__def_' in attr:
                defvals[attr.split('_SettingsClass__def_')[-1]] = getattr(self, attr)
        return defvals

    def addImagePath(self, path):
        if path not in self.IMG_ADDITION_PATH:
            self.IMG_ADDITION_PATH.append(path)

    def listImagePath(self):
        for path in self.IMG_ADDITION_PATH:
            yield path

    def setFindFailedDir(self, path):
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except:
                raise Exception('pikuli: can not set SettingsClass.FindFailedDir to \'%s\' -- failed to create directory.' % str(path))
        self.FindFailedDir = path

    def getFindFailedDir(self):
        return self.FindFailedDir
