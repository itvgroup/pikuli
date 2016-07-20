# -*- coding: utf-8 -*-

'''
   Patten - класс объектов, представляющих изображения, использующиеся для поиска на экране
'''

import os
import cv2

import pikuli
from _functions import *
from _exceptions import *


class Pattern(object):
    def __init__(self, img_path, similarity=None):
        '''
        img_path  --  имя файла или объект Pattern
        '''
        (self.__similarity, self.__img_path) = (None, None)

        if isinstance(img_path, Pattern):
            if similarity is None:
                similarity = img_path.getSimilarity()
            img_path   = img_path.getFilename(full_path=False)

        img_path = str(img_path)

        try:
            path = os.path.abspath(img_path)
            if os.path.exists(path) and os.path.isfile(path):
                self.__img_path = path
            else:
                for path in pikuli.Settings.listImagePath():
                    path = os.path.join(path, img_path)
                    if os.path.exists(path) and os.path.isfile(path):
                        self.__img_path = path
                        break
            if self.__img_path is None:
                raise FailExit('image file not found')


            if similarity is None:
                self.__similarity = pikuli.Settings.MinSimilarity
            elif isinstance(similarity, float) and similarity > 0.0 and similarity <= 1.0:
                self.__similarity = similarity
            else:
                raise FailExit('error around \'similarity\' parameter')

        except FailExit as e:
            raise FailExit('[error] Incorect \'Pattern\' class constructor call:\n\timg_path = %s\n\tabspath(img_path) = %s\n\tsimilarity = %s\n\tadditional comment: -{ %s }-' % (str(img_path), str(self.__img_path), str(similarity), str(e)))

        self._cv2_pattern = cv2.imread(self.__img_path)
        self.w = self._w = int(self._cv2_pattern.shape[1])
        self.h = self._h = int(self._cv2_pattern.shape[0])

    def __str__(self):
        return 'Pattern of \'%s\' with similarity = %f' % (self.__img_path, self.__similarity)

    def __repr__(self):
        return '<pikuli.Pattern.Pattern of %s' % os.path.basename(self.__img_path)

    def similar(self, similarity):
        return Pattern(self.__img_path, similarity)

    def exact(self):
        return Pattern(self.__img_path, 1.0)

    def getFilename(self, full_path=True):
        if full_path:
            return self.__img_path
        else:
            return os.path.basename(self.__img_path)

    def getSimilarity(self):
        return self.__similarity

    def getW(self):
        (self.w, self.h) = (self._w, self._h)
        return self._w

    def getH(self):
        (self.w, self.h) = (self._w, self._h)
        return self._h
