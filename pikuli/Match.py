# -*- coding: utf-8 -*-

'''
   Объекты класса Match представляют результат успешного поиска в области, представляемой объектом класса Region с использованием объекта класса Pattern.
   Имеет размеры изображения, используемого для поиска.
'''

import traceback
from . import FailExit
from . import Region


class Match(Region):
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
            super(Match, self).__init__(x, y, w, h)
            if not( score is None  or  (isinstance(score, float) and score > 0.0 and score <= 1.0) ):
                raise FailExit('not( score is None  or  (isinstance(score, float) and score > 0.0 and score <= 1.0) ):')
            self._score   = score
            self._pattern = pattern
            self.store_current_image()

        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'Match\' constructor call:\n\tx = %s\n\ty = %s\n\tw = %s\n\th = %s\n\tscore = %s\n\t' % (traceback.format_exc(), str(w), str(y), str(w), str(h), str(score)))

    def __str__(self):
        return ('<Match of \'%s\' in (%i, %i, %i, %i) with score = %.3f>' % (str(self._pattern.getFilename()), self._x, self._y, self._w, self._h, self._score))

    def __repr__(self):
        return ('<Match of \'%s\' in (%i, %i, %i, %i) with score = %.3f>' % (str(self._pattern.getFilename()), self._x, self._y, self._w, self._h, self._score))

    def getScore(self):
        ''' Sikuli: Get the similarity score the image or pattern was found. The value is between 0 and 1. '''
        return self._score

    def getTarget(self):
        ''' Sikuli: Get the 'location' object that will be used as the click point.
        Typically, when no offset was specified by Pattern.targetOffset(), the click point is the center of the matched region.
        If an offset was given, the click point is the offset relative to the center. '''
        raise NotImplementedError

    def getPattern(self):
        return self._pattern
