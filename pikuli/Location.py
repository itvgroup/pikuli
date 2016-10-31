# -*- coding: utf-8 -*-
'''
   Представляет любую точку на экране. Содержит методы для перемещения точки на экране, перемещения курсора в точку на экране, эмуляции пользовательских действий (клики, ввод текста).
'''

import logging
import time
from collections import namedtuple

import win32api
import win32con

from _functions import KeyModifier, Key, type_text, FailExit, _take_screenshot

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


class Location(object):

    def __init__(self, x, y, title=None):
        self.x = int(x)
        self.y = int(y)
        self.title = title
        self._is_mouse_down = False

    def get_color(self):
        arr = _take_screenshot(self.x, self.y, 1, 1)
        return Color(*arr.reshape(3)[::-1])

    getColor = get_color

    def __repr__(self):
        return 'Location({}, {})'.format(self.x, self.y)

    def get_xy(self):
        return self.x, self.y

    def getX(self):
        return self.x

    def getY(self):
        return self.y

    def mouseMove(self, delay=DELAY_AFTER_MOUSE_MOVEMENT):
        win32api.SetCursorPos((self.x, self.y))
        time.sleep(delay)

    def offset(self, dx, dy):
        if isinstance(dx, int) and isinstance(dy, int):
            return Location(self.x + dx, self.y + dy)
        raise FailExit('Location.offset: incorrect offset values')

    def above(self, dy):
        if isinstance(dy, int) and dy >= 0:
            return Location(self.x, self.y - dy)
        raise FailExit('Location.above: incorrect value')

    def below(self, dy):
        if isinstance(dy, int) and dy >= 0:
            return Location(self.x, self.y + dy)
        raise FailExit('Location.below: incorrect value')

    def left(self, dx):
        if isinstance(dx, int) and dx >= 0:
            return Location(self.x - dx, self.y)
        raise FailExit('Location.left: incorrect value')

    def right(self, dx):
        if isinstance(dx, int) and dx >= 0:
            return Location(self.x + dx, self.y)
        raise FailExit('Location.right: incorrect value')

    def click(self, after_cleck_delay=DEALY_AFTER_CLICK, p2c_notif=True):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)
        time.sleep(DEALY_AFTER_CLICK)
        if p2c_notif:
            logger.info('pikuli.%s.click(): click on %s' % (type(self).__name__, str(self)))

    def mouseDown(self, p2c_notif=True):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        if p2c_notif:
            logger.info('pikuli.%s.mouseDown(): mouseDown on %s' % (type(self).__name__, str(self)))

    def mouseUp(self, p2c_notif=True):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)
        if p2c_notif:
            logger.info('pikuli.%s.mouseUp(): mouseUp on %s' % (type(self).__name__, str(self)))

    def rightClick(self, after_cleck_delay=DEALY_AFTER_CLICK, p2c_notif=True):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, self.x, self.y, 0, 0)
        time.sleep(DEALY_AFTER_CLICK)
        if p2c_notif:
            logger.info('pikuli.%s.rightClick(): rightClick on %s' % (type(self).__name__, str(self)))

    def doubleClick(self, after_cleck_delay=DEALY_AFTER_CLICK, p2c_notif=True):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)
        time.sleep(DELAY_MOUSE_DOUBLE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)
        time.sleep(DEALY_AFTER_CLICK)
        if p2c_notif:
            logger.info('pikuli.%s.doubleClick(): doubleClick on %s' % (type(self).__name__, str(self)))

    def scroll(self, direction=1, count=1, click=True, p2c_notif=True):
        # direction:
        #   1 - forward
        #  -1 - backward
        self.mouseMove()
        if click:
            self.click(p2c_notif=False)
        logger.info('{} scrolling: direction={}, '
                         'count={}...'.format(self, direction, count))
        for i in range(0, int(count)):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, self.x, self.y, int(direction), 0)
            time.sleep(DELAY_IN_MOUSE_CLICK)
        if p2c_notif:
            logger.info('pikuli.%s.scroll(): scroll on %s; direction=%s, count=%s, click=%s' % (type(self).__name__, str(self), str(direction), str(count), str(click)))

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
            f = lambda x, y: Location(x, y).mouseMove(delay)
        else:
            (a1, b1, a2, b2) = (self.y, self.x, dest_y, dest_x)
            f = lambda x, y: Location(y, x).mouseMove(delay)

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
        self.x = dest_x
        self.y = dest_y
        return self

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
