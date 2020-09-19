# -*- coding: utf-8 -*-
'''
   Представляет любую точку на экране. Содержит методы для перемещения точки на экране, перемещения курсора в точку на экране, эмуляции пользовательских действий (клики, ввод текста).
'''

import logging
import time
from collections import namedtuple
from contextlib import contextmanager

from pikuli.input import InputEmulator, KeyModifier, Key, ScrollDirection, ButtonCode
from pikuli._exceptions import PostMoveCheck
from pikuli._functions import FailExit, _take_screenshot

from .vector import Vector, RelativeVec


DRAGnDROP_MOVE_DELAY = 0.005
DRAGnDROP_MOVE_STEP  = 6

Color = namedtuple('Color', 'r g b')

from pikuli import logger
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
        abs_vec = Vector(base_reg.top_left) + Vector(rel_vec).hprod(Vector(base_reg.w, base_reg.h)) // 100
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
        return tuple(self.rel)

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

    def mouse_move(self, delay=0):
        """
        :return: Положения курсора, где мышка действительно оказалась.
        :rtype: :class:`Location`
        """
        Location(InputEmulator.get_mouse_pos()).moveto(self)
        time.sleep(delay)
        new_loc = Location(InputEmulator.get_mouse_pos())
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

    def click(self, after_cleck_delay=0, p2c_notif=True):
        with InputEmulator.block_input():
            self.mouse_move()
            time.sleep(0.1)
            InputEmulator.left_click()
            if p2c_notif:
                logger.info('pikuli.%s.click(): click on %s' % (type(self).__name__, str(self)))

    def mouseDown(self, button='left', p2c_notif=True):
        with InputEmulator.block_input():
            self.mouse_move()
            btn_code = ButtonCode.LEFT if button == 'left' else ButtonCode.RIGHT
            InputEmulator.press_button(btn_code)
            if p2c_notif:
                logger.info('pikuli.%s.mouseDown(): mouseDown on %s' % (type(self).__name__, str(self)))

    def mouseUp(self, button='left', p2c_notif=True):
        with InputEmulator.block_input():
            self.mouse_move()
            btn_code = ButtonCode.LEFT if button == 'left' else ButtonCode.RIGHT
            InputEmulator.release_button(btn_code)
            if p2c_notif:
                logger.info('pikuli.%s.mouseUp(): mouseUp on %s' % (type(self).__name__, str(self)))

    def click_and_hold(self, delay, p2c_notif=True):
        with InputEmulator.block_input():
            self.mouse_move()
            InputEmulator.press_button(ButtonCode.LEFT)
            time.sleep(delay)
            InputEmulator.release_button(ButtonCode.LEFT)
            if p2c_notif:
                logger.info('pikuli.%s.click_and_hold(): click_and_hold on %s' % (type(self).__name__, str(self)))

    def click_move_hold(self, to, delay, p2c_notif=True):
        """
        Нажимает левую кнопку мыши, перемещает курсор мыши в `to`, держит нажатым
        `delay` времени, потом отпускает мышь
        :param to:
        :param delay: время в течении которого держим кнопку нажатой после перемещения мыши
        :return: :class:`Location`
        """
        with InputEmulator.block_input():
            self.mouse_move()
            InputEmulator.press_button(ButtonCode.LEFT)
            time.sleep(1)
            InputEmulator.set_mouse_pos(to.x, to.y)
            '''
            TODO: ??? почему я тут сделал через событие, а не win32api.SetCursorPos ???
            screen_w = win32api.GetSystemMetrics(0)
            screen_h = win32api.GetSystemMetrics(1)
            to_x = to.x * (65535 / screen_w)
            to_y = to.y * (65535 / screen_h)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE, to_x, to_y)
            '''
            time.sleep(delay)
            InputEmulator.release_button(ButtonCode.LEFT)
            if p2c_notif:
                logger.info('pikuli.{}.click_move_hold(): moved to x {}, y {}'.format(type(self).__name__, to.x, to.y))

    def rightClick(self, after_cleck_delay=0, p2c_notif=True):
        with InputEmulator.block_input():
            self.mouse_move()
            InputEmulator.right_click()
            time.sleep(after_cleck_delay)
            if p2c_notif:
                logger.info('pikuli.%s.rightClick(): rightClick on %s' % (type(self).__name__, str(self)))

    def doubleClick(self, after_cleck_delay=0, p2c_notif=True):
        with InputEmulator.block_input():
            self.mouse_move()
            InputEmulator.left_dbl_click()
            time.sleep(after_cleck_delay)
            if p2c_notif:
                logger.info('pikuli.%s.doubleClick(): doubleClick on %s' % (type(self).__name__, str(self)))

    def scroll(self, direction, count, click=True, modifiers=None, p2c_notif=True):
        # direction:
        #   1 - forward
        #  -1 - backward
        with InputEmulator.block_input():
            self.mouse_move()
            if modifiers is not None:
                InputEmulator.press_modifiers(modifiers)
            if click:
                self.click(p2c_notif=False)
            logger.info('{} scrolling: direction={}, '
                             'count={}...'.format(self, direction, count))
            InputEmulator.scroll(
                ScrollDirection.UP if direction == 1 else ScrollDirection.DOWN,
                count=int(count))
            if p2c_notif:
                logger.info('pikuli.%s.scroll(): scroll on %s; direction=%s, count=%s, click=%s' % (type(self).__name__, str(self), str(direction), str(count), str(click)))
            if modifiers is not None:
                InputEmulator.release_modifiers(modifiers)

    def type(self, text, modifiers=None, click=True, press_enter=False, click_type_delay=0, p2c_notif=True):
        ''' Не как в Sikuli '''
        if click:
            self.click(after_cleck_delay=click_type_delay, p2c_notif=False)

        InputEmulator.type_text(text, modifiers, p2c_notif=False)

        if press_enter:
            InputEmulator.type_key(Key.ENTER)

        if p2c_notif:
            logger.info('pikuli.%s.type(): type on %s \'%s\'; modifiers=%s, click=%s' % (type(self).__name__, str(self), repr(text), str(modifiers), str(click)))

    def enter_text(self, text, modifiers=None, click=True, click_type_delay=0, p2c_notif=True, press_enter=True):
        '''
        ПЕРЕСТАТЬ ИСПОЛЬБЗОВАТЬ ЭТОТ МЕТОД
        Не как в Sikuli
        TODO: не нужен тут Ctrl+a  --  не всегда и не везде работает
        '''
        self.type('a', KeyModifier.CTRL, click=click, press_enter=False, p2c_notif=False)
        time.sleep(0.5)
        self.type(text, modifiers, click=False, press_enter=press_enter, p2c_notif=False)

        if p2c_notif:
            logger.info('pikuli.%s.enter_text(): enter_text on %s \'%s\'; modifiers=%s, click=%s' % (type(self).__name__, str(self), repr(text), str(modifiers), str(click)))

        logger.warning('We need to eliminate all calls of Location.enter_text() !!!!!')

    @staticmethod
    def points_between_points(src_x, src_y, dest_x, dest_y, move_step):
        points = []
        delta_x = abs(dest_x - src_x)
        delta_y = abs(dest_y - src_y)
        if src_x < dest_x:
            sign_x = move_step
        else:
            sign_x = -move_step

        if src_y < dest_y:
            sign_y = move_step
        else:
            sign_y = -move_step

        error = delta_x - delta_y

        points.append((src_x, src_y))
        while LocationF(src_x, src_y).distance_to( dest_x, dest_y) > move_step:
            points.append((src_x, src_y))
            error_2 = error * 2

            if error_2 > -delta_y:
                error -= delta_y
                src_x += sign_x

            if error_2 < delta_x:
                error += delta_x
                src_y += sign_y
        points.append((dest_x, dest_y))
        return points

    def moveto(self, dest_location, move_step=DRAGnDROP_MOVE_STEP):
        """
        Функция двигает курсор по напрвлению к точке назначения по прямой

        :param move_step:
        :type dest_location:
        """
        if isinstance(dest_location, Location):
            (src_x, src_y, dest_x, dest_y) = (self._x_int, self._y_int, dest_location._x_int, dest_location._y_int)
        else:
            assert len(dest_location) == 2
            (src_x, src_y, dest_x, dest_y) = (self._x_int, self._y_int, int(dest_location[0]), int(dest_location[1]))

        for x, y in self.points_between_points(src_x, src_y, dest_x, dest_y, move_step):
            InputEmulator.set_mouse_pos(x, y)

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
        if len(dest_location) == 1 and isinstance(dest_location[0], Location):
            (dest_x, dest_y) = (dest_location[0].x, dest_location[0].y)
        else:
            assert len(dest_location) == 2, dest_location
            (dest_x, dest_y) = (int(dest_location[0]), int(dest_location[1]))

        if not self._is_mouse_down:
            self.mouseDown(p2c_notif=False)
            self._is_mouse_down = True

        self.moveto((dest_x, dest_y), move_step=1)
        time.sleep(0.1)
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
        return (self + loc) // 2

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
