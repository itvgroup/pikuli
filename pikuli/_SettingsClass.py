# -*- coding: utf-8 -*-

import os
import tempfile


class SettingsClass(object):

    __def_IMG_ADDITION_PATH = []  # Пути, кроме текущего и мб еще какого-то подобного
    __def_MinSimilarity = 0.995  # Почти устойчиво с 0.995, но однажны не нашел узелок для контура. 0.700 -- будет найдено в каждом пикселе (порог надо поднимать выше).
    __def_FindFailedDir = os.path.join(tempfile.gettempdir(), 'find_failed')

    # Logger:
    __def_PatternURLTemplate = None  # Где искать картинки-шаблрны. Строка-шаблон с %s, куда подставляется имя файла с картинкой-шаблоном. К примеру: http://192.168.116.1/pikuli/pattern/ok_button.png

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
        _path = os.path.abspath(path)
        if not os.path.isdir(_path):
            raise Exception('pikuli.addImagePath(...): Path \'%s\' does not exist!' % str(path))
        if _path not in self.IMG_ADDITION_PATH:
            self.IMG_ADDITION_PATH.append(_path)

    def listImagePath(self):
        for path in self.IMG_ADDITION_PATH:
            yield path

    def setFindFailedDir(self, path):
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception:
                raise Exception('pikuli.setFindFailedDir(...): can not set SettingsClass.FindFailedDir to \'%s\' -- failed to create directory.' % str(path))
        self.FindFailedDir = path

    def getFindFailedDir(self):
        return self.FindFailedDir

    def setPatternURLTemplate(self, GetPattern_URLTemplate):
        self.GetPattern_URLTemplate = GetPattern_URLTemplate

    def getPatternURLTemplate(self):
        return self.GetPattern_URLTemplate
