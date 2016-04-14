# -*- coding: utf-8 -*-

'''
   Объекты класса Match представляют результат успешного поиска в области, представляемой объектом класса Region с использованием объекта класса Pattern.
   Имеет размеры изображения, используемого для поиска.
'''

import traceback
from _exceptions import *
from Region import *


class Match(Region):
    def __init__(self, x, y, w, h, score, pattern):
        try:
            super(Match, self).__init__(x, y, w, h)
            if not isinstance(score, float) or score <= 0.0 or score > 1.0:
                raise FailExit('not isinstance(score, float) or score <= 0.0 or score > 1.0:')
            self.__score  = score
            self._pattern = pattern
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'Match\' constructor call:\n\tx = %s\n\ty = %s\n\tw = %s\n\th = %s\n\tscore = %s\n\t' % (traceback.format_exc(), str(w), str(y), str(w), str(h), str(score)))

    def __str__(self):
        return ('Match of \'%s\' in (%i, %i, %i, %i) with score = %f' % (str(self._pattern.getFilename()), self._x, self._y, self._w, self._h, self.__score))

    def __repr__(self):
        return ('<Match of \'%s\' in (%i, %i, %i, %i) with score = %f>' % (str(self._pattern.getFilename()), self._x, self._y, self._w, self._h, self.__score))

    def getScore(self):
        ''' Sikuli: Get the similarity score the image or pattern was found. The value is between 0 and 1. '''
        return self.__score

    def getTarget(self):
        ''' Sikuli: Get the 'location' object that will be used as the click point.
        Typically, when no offset was specified by Pattern.targetOffset(), the click point is the center of the matched region.
        If an offset was given, the click point is the offset relative to the center. '''
        raise Exception('TODO here')
