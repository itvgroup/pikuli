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

DRAGnDROP_MOVE_DELAY = 0.005
DRAGnDROP_MOVE_STEP  = 10


class Location(object):

    def __init__(self, x, y, title=None):
        self.title = title
        try:
            self._x = self.x = int(x)
            self._y = self.y = int(y)
            self._is_mouse_down = False
        except:
            raise FailExit('[error] Incorect \'Location\' class constructor call:\n\tx = %s\n\ty = %s\n\ttitle= %s' % (str(x), str(y), str(title)))

    def __str__(self):
        (self.x, self.y) = (self._x, self._y)
        return 'Location (%i, %i)' % (self._x, self._y)

    def get_xy(self):
        (self.x, self.y) = (self._x, self._y)
        return (self.x, self.y)

    def getX(self):
        (self.x, self.y) = (self._x, self._y)
        return self.x

    def getY(self):
        (self.x, self.y) = (self._x, self._y)
        return self.y

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


    def dragto(self, *dest_location):
        if len(dest_location) == 1 and isinstance(dest_location[0], Location):
            (dest_x, dest_y) = (dest_location[0].x, dest_location[0].y)
        elif len(dest_location) == 2:
            try:
                (dest_x, dest_y) = (int(dest_location[0]), int(dest_location[1]))
            except:
                raise FailExit('')
        else:
            raise FailExit('')

        if not self._is_mouse_down:
            self.mouseDown()
            self._is_mouse_down = True

        # Алгоритм Брезенхема
        # https://ru.wikipedia.org/wiki/%D0%90%D0%BB%D0%B3%D0%BE%D1%80%D0%B8%D1%82%D0%BC_%D0%91%D1%80%D0%B5%D0%B7%D0%B5%D0%BD%D1%85%D1%8D%D0%BC%D0%B0
        if abs(dest_x - self.x) >= abs(dest_y - self.y):
            (a1, b1, a2, b2) = (self.x, self.y, dest_x, dest_y)
            f = lambda x, y: Location(x, y).mouseMove(DRAGnDROP_MOVE_DELAY)
        else:
            (a1, b1, a2, b2) = (self.y, self.x, dest_y, dest_x)
            f = lambda x, y: Location(y, x).mouseMove(DRAGnDROP_MOVE_DELAY)

        k = float(b2 - b1) / (a2 - a1)
        a_sgn = (a2 - a1) / abs(a2 - a1)
        la = 0
        while abs(la) <= abs(a2 - a1):
            a = a1 + la
            b = int(k * la) + b1
            f(a, b)
            la += a_sgn * DRAGnDROP_MOVE_STEP

        self.x = self._x = dest_x
        self.y = self._y = dest_y

        return self

    def drop(self):
        if self._is_mouse_down:
            self.mouseUp()
            self._is_mouse_down = False
            return self
        else:
            raise FailExit('You try drop <%s>, but it is not bragged before!' % str(self))

    def dragndrop(self, *dest_location):
        self.dragto(*dest_location)
        self.drop()
        return self
