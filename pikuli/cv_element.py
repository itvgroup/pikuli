# -*- coding: utf-8 -*-

from . import Region
from . import Location


class CVElement(object):
    '''
    В конструктор класса передаются именно координаты области или ее центра.
    В первом случае, область опеределна полностью, во втором -- достраеивается.
    Достраивать можно просто из предположения о заранее известном размере контрола
    в пикселях. Т.о., CVElement-класс как бы "натягивается" поверх нарисованных на
    экране контролов в уже звестных местах -- внешняя функция должна распознать
    компьюетрным зрение опорные изображения и вычислить координаты области, наокторую
    "натягивать" это класс. Этим будут заниматься функции из wg-файлов.

    С дургой стороны, CVElement можно (да и правильно это будет) снабдить статическим
    методом конструирования -- если его вызвать, то он вернет объект(ы) соответствующего
    дочернего к CVElement класса, соответствующие искомым контролам.

    Но не будем эти классы использовать для построение иерархии контролов -- для этого
    у нас есть wdb. Будем этого рода классы использовать именно для удобного получения
    к функциям контрола (изменить поле, нажать конктреную кнопку и т.п.)
    '''

    def __init__(self, where_it_is):
        if isinstance(where_it_is, Region):
            self._reg = where_it_is
            where_it_is = where_it_is.center
        if not isinstance(where_it_is, Location):
            raise Exception(
                'pikuli.cv_element.CVElement.__init__(): '
                'input argument must be pikuli.Region or '
                'pikuli.Location treating as a center '
                'of the control:\n\twhere_it_is = %s' % str(where_it_is))
        self._center = where_it_is
        if not hasattr(self, '_reg'):
            self._reg = Region(self._center.x, self._center.y, 1, 1)
        if self._reg.x == 0 or self._reg.y == 0:
            raise Exception(
                'pikuli.cv_element.CVElement.__init__(): '
                'you try to create \'%s\' with icvorrect width '
                'or height:\n\t self._reg = %s' % (type(self).__name__, str(self._reg)))

    def reg(self):
        return self._reg

    @classmethod
    def find_us_in(cls, reg):
        raise NotImplementedError(
            'pikuli.cv_element.CVElement.find_us_in(): '
            '[INTERNAL ERROR] You shoud implement this method '
            'in child classes!')
