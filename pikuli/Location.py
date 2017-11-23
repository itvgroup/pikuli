# -*- coding: utf-8 -*-
'''
   Представляет любую точку на экране. Содержит методы для перемещения точки на экране, перемещения курсора в точку на экране, эмуляции пользовательских действий (клики, ввод текста).
'''

import logging
import time
from collections import namedtuple

import win32api
import win32con

from ._functions import KeyModifier, Key, type_text, FailExit, _take_screenshot, press_modifiers, release_modifiers
from .Vector import Vector, RelativeVec

DELAY_AFTER_MOUSE_MOVEMENT = 0.500  # Время в [c]
DELAY_IN_MOUSE_CLICK = 0.100        # Время в [c] между нажатием и отжатием кнопки (замерял сам и гуглил)
DELAY_MOUSE_DOUBLE_CLICK = 0.100    # Время в [c] между кликами (замерял сам и гуглил)
DELAY_KBD_KEY_PRESS = 0.020

DEALY_AFTER_CLICK            = 0.3  # В частности, время бездейставия между кликом в область и началом введения текста (по умолчанию).
DELAY_BETWEEN_CLICK_AND_TYPE = DEALY_AFTER_CLICK

DRAGnDROP_MOVE_DELAY = 0.005
DRAGnDROP_MOVE_STEP  = 10

Color = namedtuple('Color', 'r g b')

logger = logging.getLogger('axxon.pikuli')

"""
TODO: Unit Test

l1 = Location(3, 4)
l2 = Location(1, 1)

print 'l1, l2:  ', l1, l2
print 'l1 + l2: ', l1 + l2
print 'l1 - l2: ', l1 - l2
print 'l1 * l2: ', l1 * l2
print 'abs(l1): ', abs(l1)
print 'l1 * 2.1:', l1 * 2.1
print 'l1 / 2.1:', l1 / 2.1
print 'abs(l1): ', abs(l1)
print l1.midpoint_to(l2)
print l1.distance_to(l2)

rel_l = Location.from_rel(Region(0,0,50,50), 0.15, 0.15)
print rel_l, rel_l.x, rel_l._x
print rel_l.rel.x

"""

class LocationF(Vector):

    def __init__(self, *args, **kwargs):
        """
        Координаты, хранимые в классе, ещё вещественные.
        :param args: Либо один кземпляр :class:`Vector` или :class:`Location`, либо пара коорлинат `x, y`.
        :param kwargs: `title=None`
        """
        super(LocationF, self).__init__(*args)

        self.title = kwargs.pop('title', None)
        self.base_reg = kwargs.pop('base_reg', None)
        assert not kwargs, 'kwargs = {}'.format(kwargs)

        self._is_mouse_down = False

    @classmethod
    def from_rel(cls, base_reg, *args):
        """
        :param args: "x, y" из [0.0; 100.0] относительно левого верхнего угла `base_reg`
        :type args: Пара `x, y` или :class:`RelativeVec`
        :param base_reg: Базовая область. Относительные координаты считаются на основе левого
                         верхнего угла этого прямоугольника.
        :type base_reg: :class:`Region`
        """
        rel_vec = RelativeVec(*args)
        abs_vec = Vector(base_reg.top_left) + Vector(rel_vec).hprod(Vector(base_reg.w, base_reg.h)) / 100
        return cls(abs_vec, base_reg=base_reg)

    @property
    def rel(self):
        """
        Возвращает :class:`Vector` относительных координат. Доступно для экземпляра :class:`Location`
        просто под именем `rel` (переопределяет `@classmethod` :func:`Location.rel`).
        :rtype: :class:`Vector`
        """
        assert self.base_reg
        diff_vec = Vector(self - self.base_reg.top_left)
        rel_vec = diff_vec.hprod(Vector(self.base_reg.w, self.base_reg.h).hinv) * 100
        return RelativeVec(rel_vec)

    @property
    def rel_xy(self):
        return tupe(self.rel)

    @property
    def rel_x(self):
        return self.rel.x

    @property
    def rel_y(self):
        return self.rel.y

    @property
    def _x_int(self):
        return int(round(self._x))

    @property
    def _y_int(self):
        return int(round(self._y))

    def get_color(self):
        arr = _take_screenshot(self._x_int, self._y_int, 1, 1)
        return Color(*arr.reshape(3)[::-1])

    def mouse_move(self, delay=DELAY_AFTER_MOUSE_MOVEMENT):
        """
        :return: Положения курсора, где мышка действительно оказалась.
        :rtype: :class:`Location`
        """
        win32api.SetCursorPos((self._x_int, self._y_int))
        time.sleep(delay)
        new_loc = self.__class__(win32api.GetCursorPos())
        if new_loc != self:
            logger.warning('{}.mouse_move: new_loc={} != {}=self'.format(self.__class__, new_loc, self))
        return new_loc

    def offset(self, dx, dy):
        return self + Vector(dx, dy)

    def above(self, dy):
        return self - Vector(0, dy)

    def below(self, dy):
        return self + Vector(0, dy)

    def left(self, dx):
        return self - Vector(dx, 0)

    def right(self, dx):
        return self + Vector(dx, 0)

    def _mouse_event(self, event, direction=0):
        return win32api.mouse_event(event, self._x_int, self._y_int, direction, 0)

    def click(self, after_cleck_delay=DEALY_AFTER_CLICK, p2c_notif=True):
        self.mouse_move()
        self._mouse_event(win32con.MOUSEEVENTF_LEFTDOWN)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        self._mouse_event(win32con.MOUSEEVENTF_LEFTUP)
        time.sleep(DEALY_AFTER_CLICK)
        if p2c_notif:
            logger.info('pikuli.%s.click(): click on %s' % (type(self).__name__, str(self)))

    def mouseDown(self, button='left', p2c_notif=True):
        self.mouse_move()
        if button == 'left':
            self._mouse_event(win32con.MOUSEEVENTF_LEFTDOWN)
        else:
            self._mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN)
        if p2c_notif:
            logger.info('pikuli.%s.mouseDown(): mouseDown on %s' % (type(self).__name__, str(self)))

    def mouseUp(self, button='left', p2c_notif=True):
        self.mouse_move()
        if button == 'left':
            self._mouse_event(win32con.MOUSEEVENTF_LEFTUP)
        else:
            self._mouse_event(win32con.MOUSEEVENTF_RIGHTUP)
        if p2c_notif:
            logger.info('pikuli.%s.mouseUp(): mouseUp on %s' % (type(self).__name__, str(self)))

    def rightClick(self, after_cleck_delay=DEALY_AFTER_CLICK, p2c_notif=True):
        self.mouse_move()
        self._mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        self._mouse_event(win32con.MOUSEEVENTF_RIGHTUP)
        time.sleep(DEALY_AFTER_CLICK)
        if p2c_notif:
            logger.info('pikuli.%s.rightClick(): rightClick on %s' % (type(self).__name__, str(self)))

    def doubleClick(self, after_cleck_delay=DEALY_AFTER_CLICK, p2c_notif=True):
        self.mouse_move()
        self._mouse_event(win32con.MOUSEEVENTF_LEFTDOWN)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        self._mouse_event(win32con.MOUSEEVENTF_LEFTUP)
        time.sleep(DELAY_MOUSE_DOUBLE_CLICK)
        self._mouse_event(win32con.MOUSEEVENTF_LEFTDOWN)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        self._mouse_event(win32con.MOUSEEVENTF_LEFTUP)
        time.sleep(DEALY_AFTER_CLICK)
        if p2c_notif:
            logger.info('pikuli.%s.doubleClick(): doubleClick on %s' % (type(self).__name__, str(self)))

    def scroll(self, direction, count, click=True, modifiers=None, p2c_notif=True):
        # direction:
        #   1 - forward
        #  -1 - backward
        if modifiers is not None:
            press_modifiers(modifiers)
        self.mouse_move()
        if click:
            self.click(p2c_notif=False)
        logger.info('{} scrolling: direction={}, '
                         'count={}...'.format(self, direction, count))
        for i in range(0, int(count)):
            self._mouse_event(win32con.MOUSEEVENTF_WHEEL, direction=int(direction))
            time.sleep(DELAY_IN_MOUSE_CLICK)
        if p2c_notif:
            logger.info('pikuli.%s.scroll(): scroll on %s; direction=%s, count=%s, click=%s' % (type(self).__name__, str(self), str(direction), str(count), str(click)))
        if modifiers is not None:
            release_modifiers(modifiers)

    def type(self, text, modifiers=None, click=True, press_enter=False,
             click_type_delay=DELAY_BETWEEN_CLICK_AND_TYPE,
             p2c_notif=True):
        ''' Не как в Sikuli '''
        if click:
            self.click(after_cleck_delay=click_type_delay, p2c_notif=False)
        _text = str(text) + (Key.ENTER if press_enter else '')
        type_text(_text, modifiers, p2c_notif=False)
        if p2c_notif:
            logger.info('pikuli.%s.type(): type on %s \'%s\'; modifiers=%s, click=%s' % (type(self).__name__, str(self), repr(text), str(modifiers), str(click)))

    def enter_text(self, text, modifiers=None, click=True, click_type_delay=DELAY_BETWEEN_CLICK_AND_TYPE, p2c_notif=True):
        ''' Не как в Sikuli
        TODO: не нужен тут Ctrl+a  --  не всегда и не везде работает'''
        if click:
            self.click(after_cleck_delay=click_type_delay, p2c_notif=False)
        type_text('a', KeyModifier.CTRL, p2c_notif=False)
        time.sleep(0.5)
        type_text(str(text) + Key.ENTER, modifiers, p2c_notif=False)
        if p2c_notif:
            logger.info('pikuli.%s.enter_text(): enter_text on %s \'%s\'; modifiers=%s, click=%s' % (type(self).__name__, str(self), repr(text), str(modifiers), str(click)))

        logger.warning('We need to eliminate all calls '
                            'of Location.enter_text() !!!!!')

    def moveto(self, dest_location):
        """
        Функция двигает курсор по напрвлению к точке назначения по прямой

        :type dest_location: :class:`Location`
        """
        (dest_x, dest_y) = (None, None)
        if hasattr(dest_location, 'x') and hasattr(dest_location, 'y'):
            (dest_x, dest_y) = (dest_location.x, dest_location.y)
        else:
            assert len(dest_location) == 2
            (dest_x, dest_y) = (dest_location[0], dest_location[1])
        if dest_x is None or dest_y is None:
            raise FailExit('')

        if abs(dest_x - self.x) >= abs(dest_y - self.y):
            (a1, b1, a2, b2) = (self.x, self.y, dest_x, dest_y)
            f = lambda x, y: Location(x, y).mouse_move(DRAGnDROP_MOVE_DELAY)
        else:
            (a1, b1, a2, b2) = (self.y, self.x, dest_y, dest_x)
            f = lambda x, y: Location(y, x).mouse_move(DRAGnDROP_MOVE_DELAY)

        if a2 != a1:
            k = float(b2 - b1) / (a2 - a1)
            a_sgn = (a2 - a1) / abs(a2 - a1)
            la = 0
            while abs(la) <= abs(a2 - a1):
                a = a1 + la
                b = int(k * la) + b1
                f(a, b)
                la += a_sgn * DRAGnDROP_MOVE_STEP

        self._x = dest_x
        self._y = dest_y
        return self

    def moveto_rel(self, *dest_location):
        """
        То же, что и :func:`Location.moveto`, но принимает относительные координаты. Работает, если
        задано поле `Location.base_reg`.

        :param dest_location: Относительные координаты в виде двух чисел `x` и `y`, `tuple`'а
                              `(x,y)` или :class:`Vector`.
        """
        return self.moveto(Location.rel(self.base_reg, *dest_location))

    def dragto(self, *dest_location, **kwargs):
        p2c_notif = kwargs.pop('p2c_notif', True)
        if len(kwargs) != 0:
            raise Exception('Illegal arguments of pikuli.Location.dragto(): %s' % str(kwargs))

        if len(dest_location) == 1 and isinstance(dest_location[0], Location):
            (dest_x, dest_y) = (dest_location[0].x, dest_location[0].y)
            delay = DRAGnDROP_MOVE_DELAY
        elif len(dest_location) == 2:
            try:
                (dest_x, dest_y) = (int(dest_location[0]), int(dest_location[1]))
            except Exception:
                raise FailExit('')
            delay = DRAGnDROP_MOVE_DELAY
        elif len(dest_location) == 3:
            try:
                (dest_x, dest_y) = (int(dest_location[0]), int(dest_location[1]))
            except Exception:
                raise FailExit('')
            delay = float(dest_location[2])

        else:
            raise FailExit('')

        if not self._is_mouse_down:
            self.mouseDown(p2c_notif=False)
            self._is_mouse_down = True

        # Алгоритм Брезенхема
        # https://ru.wikipedia.org/wiki/%D0%90%D0%BB%D0%B3%D0%BE%D1%80%D0%B8%D1%82%D0%BC_%D0%91%D1%80%D0%B5%D0%B7%D0%B5%D0%BD%D1%85%D1%8D%D0%BC%D0%B0
        if abs(dest_x - self.x) >= abs(dest_y - self.y):
            (a1, b1, a2, b2) = (self.x, self.y, dest_x, dest_y)
            f = lambda x, y: Location(x, y).mouse_move(delay)
        else:
            (a1, b1, a2, b2) = (self.y, self.x, dest_y, dest_x)
            f = lambda x, y: Location(y, x).mouse_move(delay)
        if a2 != a1:
        if a2 != a1:
            k = float(b2 - b1) / (a2 - a1)
            a_sgn = (a2 - a1) / abs(a2 - a1)
            la = 0
            while abs(la) <= abs(a2 - a1):
                a = a1 + la
                b = int(k * la) + b1
                f(a, b)
                la += a_sgn * DRAGnDROP_MOVE_STEP

        if p2c_notif:
            logger.info('pikuli.%s.dragto(): drag %s to (%i,%i)' % (type(self).__name__, str(self), self.x, self.y))
        self._x = dest_x
        self._y = dest_y
        return self

    def dragto_rel(self, *dest_location, **kwargs):
        """
        То же, что и :func:`Location.dragto`, но принимает относительные координаты. Работает, если
        задано поле `Location.base_reg`.

        :param dest_location: Относительные координаты в виде двух чисел `x` и `y`, `tuple`'а
                              `(x,y)` или :class:`Vector`.
        """
        return self.dragto(Location.rel(self.base_reg, *dest_location), **kwargs)

    def drop(self, p2c_notif=True):
        if self._is_mouse_down:
            self.mouseUp(p2c_notif=False)
            self._is_mouse_down = False
            if p2c_notif:
                logger.info('pikuli.%s.drop(): drop %s' % (type(self).__name__, str(self)))
            return self
        else:
            raise FailExit('You try drop <%s>, but it is not bragged before!' % str(self))

    def dragndrop(self, *dest_location, **kwargs):
        p2c_notif = kwargs.pop('p2c_notif', True)
        if len(kwargs) != 0:
            raise Exception('Illegal arguments of pikuli.Location.dragndrop(): %s' % str(kwargs))

        src = str(self)
        self.dragto(*dest_location, p2c_notif=False)
        self.drop(p2c_notif=False)
        if p2c_notif:
            logger.info('pikuli.%s.dragto(): drag %s to (%i,%i) and drop' % (type(self).__name__, src, self.x, self.y))
        return self

    drag_and_drop = dragndrop

    def dragndrop_rel(self, *dest_location, **kwargs):
        """
        То же, что и :func:`Location.dragndrop`, но принимает относительные координаты. Работает, если
        задано поле `Location.base_reg`.

        :param dest_location: Относительные координаты в виде двух чисел `x` и `y`, `tuple`'а
                              `(x,y)` или :class:`Vector`.
        """
        return self.dragndrop(Location.rel(self.base_reg, *dest_location), **kwargs)

    def midpoint_to(self, *args):
        """
        Считает координаты середины отрезка, соединяющего текущую точку и ту, что в указана  аргументах

        :param args: экземпляр :class:`Location` или пара `x, y`
        :return type: :class:`Location`
        """
        loc = Location(*args)
        return (self + loc) / 2

    def distance_to(self, *args):
        """
        Считает расстояние между текуей точкой и той, что в указана аргументах

        :param args: экземпляр :class:`Location` или пара `x, y`
        :return type: `float`
        """
        loc = Location(*args)
        return abs(self - loc)


class Location(LocationF):

    def __init__(self, *args, **kwargs):
        """
        Координаты, хранимые в классе, уже целочисленные.
        :param args: Либо один кземпляр :class:`Vector` или :class:`Location`, либо пара коорлинат `x, y`.
        :param kwargs: `title=None`
        """
        super(Location, self).__init__(*args, **kwargs)
        self._x, self._y = self._x_int, self._y_int

    @property
    def x(self):
        return self._x_int

    @property
    def y(self):
        return self._y_int

    def __eq__(self, other):
        return self.xy == other.xy

    def __ne__(self, other):
        return self.xy != other.xy
