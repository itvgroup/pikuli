# -*- coding: utf-8 -*-

'''
   Объекты класса Match представляют результат успешного поиска в области, представляемой объектом класса Region с использованием объекта класса Pattern.
   Имеет размеры изображения, используемого для поиска.
'''

import traceback

from .. import FailExit
from ..geom import Region

class Match:
    '''
        Как потомок Region, класс Match сможет хранить в себе картинку в формате numpy.array; сравнивать
        сохраненную картинку с тем, что сейчас в области (x, y, w, h) отображается на экране. Будем по
        умолчанию в конструкторе Match'а сохранять то, что есть на экране.
    '''

    def __init__(self, x, y, w, h, pattern, score):
        '''
            x, y, w, h  --  области экрана ПК, которая содержит в себе искомый шаблон pattern
            pattern     --  искомый шаблон в формате pikuli.Pattern
            score       --  число, показывающее достоверность совпадения шаблона с изображение на экране
        '''
        try:
            if not( (score is None) or (isinstance(score, float) and score > 0.0 and score <= 1.0) ):
                raise FailExit('not( score is None  or  (isinstance(score, float) and score > 0.0 and score <= 1.0) ):')
            self._region  = Region(x, y, w, h)
            self._img     = self._region.cv.take_screenshot()
            self._score   = score
            self._pattern = pattern

        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'Match\' constructor call:\n\tx = %s\n\ty = %s\n\tw = %s\n\th = %s\n\tscore = %s\n\t' % (traceback.format_exc(), str(w), str(y), str(w), str(h), str(score)))

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return f'<Match of \'{self._pattern.filename}\' in {self._region} with score = {self._score:.3f}>'

    @property
    def region(self):
        return self._region

    @property
    def score(self):
        ''' Sikuli: Get the similarity score the image or pattern was found. The value is between 0 and 1. '''
        return self._score

    @property
    def pattern(self):
        return self._pattern
