# -*- coding: utf-8 -*-
'''
   Представляет любую точку на экране. Содержит методы для перемещения точки на экране, перемещения курсора в точку на экране, эмуляции пользовательских действий (клики, ввод текста).
'''
import win32api
import win32con
import time
from _functions import *


DELAY_AFTER_MOUSE_MOVEMENT = 0.500  # Время в [c]
DELAY_IN_MOUSE_CLICK = 0.100        # Время в [c] между нажатием и отжатием кнопки (замерял сам и гуглил)
DELAY_MOUSE_DOUBLE_CLICK = 0.100    # Время в [c] между кликами (замерял сам и гуглил)
DELAY_KBD_KEY_PRESS = 0.020

DEALY_AFTER_CLICK            = 0.3  # В частности, время бездейставия между кликом в область и началом введения текста (по умолчанию).
DELAY_BETWEEN_CLICK_AND_TYPE = DEALY_AFTER_CLICK


class Location(object):

    def __init__(self, x, y, title=None):
        (self.x, self.y, self._x, self._y) = (None, None, None, None)
        self.title = title

        try:
            if not (isinstance(x, int) and isinstance(y, int)):
                raise FailExit()

            self._x = self.x = x
            self._y = self.y = y

        except FailExit:
            raise FailExit('[error] Incorect \'Location\' class constructor call:\n\tx = %s\n\ty = %s\n\ttitle= %s' % (str(x), str(y), str(title)))

    def __str__(self):
        (self.x, self.y) = (self._x, self._y)
        return 'Location (%i, %i)' % (self._x, self._y)

    def mouseMove(self, delay=DELAY_AFTER_MOUSE_MOVEMENT):
        win32api.SetCursorPos((self.x, self.y))
        time.sleep(delay)

    def offset(self, dx, dy):
        if isinstance(dx, int) and isinstance(dy, int):
            return Location(self.x + dx, self.y + dy)
        else:
            raise FailExit('Location.offset: incorrect offset values')

    def above(self, dy):
        if isinstance(dy, int) and dy >= 0:
            return Location(self.x, self.y - dy)
        else:
            raise FailExit('Location.above: incorrect value')

    def below(self, dy):
        if isinstance(dy, int) and dy >= 0:
            return Location(self.x, self.y + dy)
        else:
            raise FailExit('Location.below: incorrect value')

    def left(self, dx):
        if isinstance(dx, int) and dx >= 0:
            return Location(self.x - dx, self.y)
        else:
            raise FailExit('Location.left: incorrect value')

    def right(self, dx):
        if isinstance(dx, int) and dx >= 0:
            return Location(self.x + dx, self.y)
        else:
            raise FailExit('Location.right: incorrect value')

    def click(self, after_cleck_delay=DEALY_AFTER_CLICK):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)
        time.sleep(DEALY_AFTER_CLICK)

    def mouseDown(self):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)

    def mouseUp(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)

    def rightClick(self, after_cleck_delay=DEALY_AFTER_CLICK):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, self.x, self.y, 0, 0)
        time.sleep(DEALY_AFTER_CLICK)

    def doubleClick(self, after_cleck_delay=DEALY_AFTER_CLICK):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)
        time.sleep(DELAY_MOUSE_DOUBLE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)
        time.sleep(DEALY_AFTER_CLICK)

    def scroll(self, direction=1, count=1, click=True):
        # direction:
        #   1 - forward
        #  -1 - backward
        self.mouseMove()
        if click:
            self.click()
        for i in range(0, int(count)):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, self.x, self.y, int(direction), 0)
            time.sleep(DELAY_IN_MOUSE_CLICK)

    def type(self, text, modifiers=None, click=True, click_type_delay=DELAY_BETWEEN_CLICK_AND_TYPE):
        ''' Не как в Sikuli '''
        if click:
            self.click(after_cleck_delay=click_type_delay)
        type_text(str(text), modifiers)

    def enter_text(self, text, modifiers=None, click=True, click_type_delay=DELAY_BETWEEN_CLICK_AND_TYPE):
        ''' Не как в Sikuli '''
        if click:
            self.click(after_cleck_delay=click_type_delay)
        type_text('a', KeyModifier.CTRL)
        type_text(str(text) + Key.ENTER, modifiers)
