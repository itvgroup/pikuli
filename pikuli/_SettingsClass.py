# -*- coding: utf-8 -*-

#import os
#import sys

#from _functions import p2c


class SettingsClass(object):

    __def_IMG_ADDITION_PATH = []  # Пути, кроме текущего и мб еще какого-то подобного
    __def_MinSimilarity = 0.995  # 0.700 -- и будет найдено в каждом пикселе. Порог надо поднимать повыше.

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
