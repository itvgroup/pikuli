# -*- coding: utf-8 -*-

import os
import logging
import cv2

import pikuli
from .File import File
from ._exceptions import FailExit
from pikuli import logger


class Pattern(File):
    """ Represents images being searched for on display. """
    def __init__(self, img_pattern, similarity=None):
        """
        :param img_pattern: Имя файла, объект Pattern или Region.
        :param str similarity: Принимает float значение от 0.0 до 1.0.
        """
        self.__similarity = None

        if isinstance(img_pattern, pikuli.Region):
            super(Pattern, self).__init__(None)
            self._cv2_pattern = img_pattern.get_raw_screenshot()

        else:
            if isinstance(img_pattern, Pattern):
                if similarity is None:
                    similarity = img_pattern.getSimilarity()
                img_path = str(img_pattern.getFilename(full_path=False))
            else:
                img_path = str(img_pattern)

            super(Pattern, self).__init__(img_path)

            try:
                path = os.path.abspath(img_path)
                if os.path.exists(path) and os.path.isfile(path):
                    self._path = path
                else:
                    for path in pikuli.Settings.listImagePath():
                        path = os.path.join(path, img_path)
                        if os.path.exists(path) and os.path.isfile(path):
                            self._path = path
                            break
                if self._path is None:
                    raise FailExit('image file not found')


                if similarity is None:
                    self.__similarity = pikuli.Settings.MinSimilarity
                elif isinstance(similarity, float) and similarity > 0.0 and similarity <= 1.0:
                    self.__similarity = similarity
                else:
                    raise FailExit('error around \'similarity\' parameter : %s' % str(similarity))

            except FailExit as e:
                raise FailExit('[error] Incorect \'Pattern\' class constructor call:\n\timg_path = %s\n\tabspath(img_path) = %s\n\tsimilarity = %s\n\tadditional comment: -{ %s }-\n\tlistImagePath(): %s' % (str(img_path), str(self._path), str(similarity), str(e), str(list(pikuli.Settings.listImagePath()))))

            self._cv2_pattern = cv2.imread(self._path)


        self.w = self._w = int(self._cv2_pattern.shape[1])
        self.h = self._h = int(self._cv2_pattern.shape[0])

    def __str__(self):
        return '<Pattern of \'%s\' with similarity = %.3f>' % (self._path, self.__similarity)

    def __repr__(self):
        return '<pikuli.Pattern.Pattern of {}>'.format(self._path and os.path.basename(self._path))

    def similar(self, similarity):
        return Pattern(self._path, similarity)

    def exact(self):
        return Pattern(self._path, 1.0)

    def getSimilarity(self):
        return self.__similarity

    def getW(self):
        self.w, self.h = self._w, self._h
        return self._w

    def getH(self):
        self.w, self.h = self._w, self._h
        return self._h

    def get_image(self):
        return self._cv2_pattern

    def save_as_png(self, full_filename):
        path = os.path.abspath(full_filename)
        logger.info('pikuli.Pattern.save_as_png:\n\tfull path: %s' % path)
        dir_path = os.path.dirname(full_filename)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        cv2.imwrite(full_filename, self._cv2_pattern)
