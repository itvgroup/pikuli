# -*- coding: utf-8 -*-

''' Пока что этот модуль -- прослойка для Sikuli. В перспективе мы сможем отказаться от Sikuli, дописывая только этот модуль

Doc pywin32:
    http://timgolden.me.uk/pywin32-docs/modules.html

Особенности использования памяти:
    -- При создании обхекта Pattern, от сделает self._cv2_pattern = cv2.imread(self.getFilename())

'''

import time
import sys
import os
import traceback

import cv2
import numpy as np

import win32api
import win32gui
import win32ui
import win32con
import win32print


RELATIONS = ['top-left', 'center']

DELAY_AFTER_MOUSE_MOVEMENT = 0.500  # Время в [c]
DELAY_IN_MOUSE_CLICK = 0.100        # Время в [c] между нажатием и отжатием кнопки (замерял сам и гуглил)
DELAY_MOUSE_DOUBLE_CLICK = 0.100    # Время в [c] между кликами (замерял сам и гуглил)
DELAY_KBD_KEY_PRESS = 0.020

DELAY_BETWEEN_CV_ATTEMPT = 0.5      # Время в [c] между попытками распознования графического объекта


def p2c(*msgs):
    for m in msgs:
        sys.__stdout__.write('*** ' + str(m) + '\n')


class FailExit(Exception):
    ''' Исключение возникает, когда обнаруживается какая-то ошибка: неправильно заданы входные аргумены, что-то не стыкуется в геметрических расчетах и т.п. '''
    pass


class FindFailed(Exception):
    ''' Исключение возникает, когда не нашли изображения на экране. '''
    pass


'''def print_exception():
    sys.__stdout__.write('\033[31m\nInitial exception:\n')
    traceback.print_exc(file=sys.__stdout__)
    sys.__stdout__.write('\033[0m\nCatched here:\n')
    sys.__stdout__.flush()'''


class _SettingsClass(object):
    __def_IMG_ADDITION_PATH = []  # Пути, кроме текущего и мб еще какого-то подобного
    __def_MinSimilarity = 0.995  # 0.700 -- и будет найдено в каждом пикселе. Порог надо поднимать повыше.

    def __init__(self):
        defvals = self.__get_default_values()
        for k in defvals:
            setattr(self, k, defvals[k])

    def __get_default_values(self):
        defvals = {}
        for attr in dir(self):
            if '_SettingsClass__def_' in attr:
                defvals[attr.split('_SettingsClass__def_')[-1]] = getattr(self, attr)
        return defvals

    def addImagePath(self, path):
        if path not in self.IMG_ADDITION_PATH:
            self.IMG_ADDITION_PATH.append(path)

    def listImagePath(self):
        for path in self.IMG_ADDITION_PATH:
            yield path

# Создадим экземпляр класса (он будет создаваться только один раз, даже если импорт модуля происходит мого раз в разных местах)
# и добавим путь к тому фйлу, из которого импортировали настоящий модуль:
Settings = _SettingsClass()
Settings.addImagePath(os.path.dirname(os.path.abspath(sys.modules['__main__'].__file__)))



def addImagePath(path):
    Settings.addImagePath(path)



def _monitor_hndl_to_screen_n(m_hndl):
    ''' Экраны-мониторы нуменруются от 1. Нулевой экран -- это полный вирутальный. '''
    minfo = win32api.GetMonitorInfo(m_hndl)  # For example for primary monitor: {'Device': '\\\\.\\DISPLAY1', 'Work': (0, 0, 1920, 1040), 'Flags': 1, 'Monitor': (0, 0, 1920, 1080)}
    screen_n = int(minfo['Device'][len(r'\\.\DISPLAY'):])
    if screen_n <= 0:
        raise FailExit('can not obtaen Screen number from win32api.GetMonitorInfo() = %s' % str(minfo))
    return screen_n


def _screen_n_to_monitor_name(n):
    ''' Экраны-мониторы нуменруются от 1. Нулевой экран -- это полный вирутальный. '''
    return r'\\.\DISPLAY%i' % n


def _screen_n_to_mon_descript(n):
    ''' Returns a sequence of tuples. For each monitor found, returns a handle to the monitor, device context handle, and intersection rectangle:
    (hMonitor, hdcMonitor, PyRECT) '''
    monitors = win32api.EnumDisplayMonitors(None, None)
    if n >= 1:
        for m in monitors:
            if _monitor_hndl_to_screen_n(m[0]) == n:
                break
    elif n == 0:
        # (x1, y1, x2, y2) = (m[2][0], m[2][1], m[2][2], m[2][3]) -- координаты углов экранов в системе кооринат большого виртуального экрана, где m -- элемнет monitors.
        x_max = max(map(lambda m: m[2][2], monitors))
        y_max = max(map(lambda m: m[2][3], monitors))
        m = (None, None, (0, 0, x_max, y_max))
    else:
        raise FailExit('wrong screen number \'%s\'' % str(n))
    return m


def _grab_screen(x, y, w, h):
    '''
    Получаем скриншот области:
            n     --  номер экрана (от нуля)
            x, y  --  верхний левый угол прямоуголника в системе координат виртуального рабочего стола
            w, h  --  размеры прямоуголника

      Любопытно, что если пытаться выйти за пределы левого монитора, читая данные из его контекста, то оставшаяся
    часть скриншота сам будет браться и из контекста другого монитора. Т.о., важно знать какому монитору принадлежит
    верхний левый угол прямоуголника, скриншот которого получаем. И не надо провериять, на каких мониторах располагаются
    остальные углы этой области. Вообще без проблем можно право и вниз уйти за пределы всех мониторов.
      Однако, надо помнить, что при копировании буфера через BitBlt() надо указывать начальные координаты с системе
    отсчета монитора, а не виртуального рабочего стола. Т.о. входные (x,y) надо пересчитывать.
    '''
    # http://stackoverflow.com/questions/3291167/how-to-make-screen-screenshot-with-win32-in-c
    # http://stackoverflow.com/questions/18733486/python-win32api-bitmap-getbitmapbits
    # http://stackoverflow.com/questions/24129253/screen-capture-with-opencv-and-python-2-7
    # Как узнать рамер экрана:
    #   Варинат 1:
    #       (_, _, scr_rect) = _screen_n_to_mon_descript(n)
    #       (w, h) = (scr_rect[2] - scr_rect[0], scr_rect[3] - scr_rect[1])
    #   Варинат 2:
    #       w = win32print.GetDeviceCaps(scr_hdc, win32con.HORZRES)
    #       h = win32print.GetDeviceCaps(scr_hdc, win32con.VERTRES)
    n = _scr_num_of_point(x, y)
    scr_hdc = win32gui.CreateDC('DISPLAY', _screen_n_to_monitor_name(n), None)

    mem_hdc = win32gui.CreateCompatibleDC(scr_hdc)  # New context of memory device. This one is compatible with 'scr_hdc'
    new_bitmap_h = win32gui.CreateCompatibleBitmap(scr_hdc, w, h)
    win32gui.SelectObject(mem_hdc, new_bitmap_h)    # Returns 'old_bitmap_h'. It will be deleted automatically.

    (_, _, m_rect) = _screen_n_to_mon_descript(n)
    win32gui.BitBlt(mem_hdc, 0, 0, w, h, scr_hdc, x-m_rect[0], y-m_rect[1], win32con.SRCCOPY)

    bmp = win32ui.CreateBitmapFromHandle(new_bitmap_h)
    bmp_info = bmp.GetInfo()
    if bmp_info['bmHeight'] != h or bmp_info['bmWidth'] != w:
        raise FailExit('bmp_info = %s, but (w, h) = (%s, %s)' % (str(bmp_info), str(w), str(h)))
    if bmp_info['bmType'] != 0 or bmp_info['bmPlanes'] != 1:
        raise FailExit('bmp_info = %s: bmType !=0 or bmPlanes != 1' % str(bmp_info))
    if bmp_info['bmBitsPixel'] % 8 != 0:
        raise FailExit('bmp_info = %s: bmBitsPixel mod. 8 is not zero' % str(bmp_info))

    bmp_arr = list(bmp.GetBitmapBits())
    del bmp_arr[3::4]  # Dele alpha channel. TODO: Is it fast enough???
    bmp_np = np.array(bmp_arr, dtype=np.uint8).reshape((h, w, 3))
    return bmp_np


def _scr_num_of_point(x, y):
    ''' Вернет номер (от нуля) того экрана, на котором располоржен левый верхний угол текущего Region. '''
    m_tl = win32api.MonitorFromPoint((x, y), win32con.MONITOR_DEFAULTTONULL)
    if m_tl is None:
        raise FailExit('top-left corner of the Region is out of visible area of sreens')
    return _monitor_hndl_to_screen_n(m_tl)


"""
def __check_reg_in_single_screen(self):
    ''' Проверяем, что Region целиком на одном экране. Экран -- это просто один из мониторав, которые существуют по мнению Windows. '''
    m_tl = win32api.MonitorFromPoint((self._x, self._y), win32con.MONITOR_DEFAULTTONULL)
    # Do "-1" to get the edge pixel belonget to the Region. The next pixel (over any direction) is out of the Region:
    m_br = win32api.MonitorFromPoint((self._x + self._w - 1, self._y + self._h - 1), win32con.MONITOR_DEFAULTTONULL)
    if m_tl is None or m_br is None:
        raise FailExit('one or more corners of region out of visible area of sreens')
    if m_tl != m_br:
        raise FailExit('region occupies more than one screen')
    return Screen(_monitor_hndl_to_screen_n(m_tl))
"""
"""
def _grab_screen_(*args):
    '''
    Получаем скриншот. Возможные наборы входных аргументов:
        Скриншот всего экрана:
            n  --  номер экрана-монитора (integer)
        Скриншот области:
            x, y, w, h  --  размеры прямоуголника
            reg         --  прямоуголник типа Region
    '''
    # http://stackoverflow.com/questions/3291167/how-to-make-screen-screenshot-with-win32-in-c
    # http://stackoverflow.com/questions/18733486/python-win32api-bitmap-getbitmapbits
    # http://stackoverflow.com/questions/24129253/screen-capture-with-opencv-and-python-2-7
    if len(args) == 1:
        if isinstance(args[0], int):
            n = args[0]
        elif isinstance(args[0], Region):
            raise Exception('TODO here')
    elif len(args) == 4:

    scr_hdc = win32gui.CreateDC('DISPLAY', _screen_n_to_monitor_name(n), None)
    mem_hdc = win32gui.CreateCompatibleDC(scr_hdc)  # New context of memory device. This one is compatible with 'scr_hdc'

    # (_, _, scr_rect) = _screen_n_to_mon_descript(n)
    # (w, h) = (scr_rect[2] - scr_rect[0], scr_rect[3] - scr_rect[1])
    w = win32print.GetDeviceCaps(scr_hdc, win32con.HORZRES)
    h = win32print.GetDeviceCaps(scr_hdc, win32con.VERTRES)
    new_bitmap_h = win32gui.CreateCompatibleBitmap(scr_hdc, w, h)
    win32gui.SelectObject(mem_hdc, new_bitmap_h)  # Returns 'old_bitmap_h'. It will be deleted automatically.
    win32gui.BitBlt(mem_hdc, 0, 0, w, h, scr_hdc, 0, 0, win32con.SRCCOPY)
"""







_KeyCodes = {
    # (bVk, bScan_press, bScan_relaese) скан коды для XT-клавиатуры. Но они могут быть многобайтовыми. Поэтому мока пробуем передавать вместо них нули.
    'ALT':   (win32con.VK_MENU, 0, 0),
    'CTRL':  (win32con.VK_CONTROL, 0, 0),
    'SHIFT': (win32con.VK_SHIFT, 0, 0),
}


class KeyModifier(object):
    ALT   = 0x01
    CTRL  = 0x02
    SHIFT = 0x04
    _rev  = {0x01: 'ALT', 0x02: 'CTRL', 0x04: 'SHIFT'}


class Key(object):
    ENTER = chr(0) + chr(win32con.VK_RETURN)
    TAB   = chr(0) + chr(win32con.VK_TAB)
    LEFT  = chr(0) + chr(win32con.VK_LEFT)
    UP    = chr(0) + chr(win32con.VK_UP)
    RIGHT = chr(0) + chr(win32con.VK_RIGHT)
    DOWN  = chr(0) + chr(win32con.VK_DOWN)


def type_text(s, modifiers=None):
    '''
    Особенности:
        -- Если установлены modifiers, то не будет различия между строчными и загалвными буксами.
           Т.е., будет игнорироваться необходимость нажимать Shift, если есть заглавные символы.
    '''
    # https://mail.python.org/pipermail/python-win32/2013-July/012862.html
    # https://msdn.microsoft.com/ru-ru/library/windows/desktop/ms646304(v=vs.85).aspx
    # http://stackoverflow.com/questions/4790268/how-to-generate-keystroke-combination-in-win32-api
    # http://stackoverflow.com/questions/11906925/python-simulate-keydown
    # https://ru.wikipedia.org/wiki/Скан-код
    # http://stackoverflow.com/questions/21197257/keybd-event-keyeventf-extendedkey-explanation-required

    def press_key(char, scancode):
        win32api.keybd_event(char, scancode, win32con.KEYEVENTF_EXTENDEDKEY, 0)  # win32con.KEYEVENTF_EXTENDEDKEY   # TODO: is scan code needed?
        time.sleep(DELAY_KBD_KEY_PRESS)

    def release_key(char, scancode):
        win32api.keybd_event(char, scancode, win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP, 0)  # win32con.KEYEVENTF_EXTENDEDKEY
        time.sleep(DELAY_KBD_KEY_PRESS)

    def type_char(char):
        press_key(char, 0)
        release_key(char, 0)

    if not isinstance(s, str):
        raise FailExit('incorrect string = \'%s\'' % str(s))

    if modifiers is not None:
        if not isinstance(modifiers, int):
            raise FailExit('incorrect modifiers = \'%s\'' % str(modifiers))
        for k in KeyModifier._rev:
            if modifiers & k != 0:
                press_key(_KeyCodes[KeyModifier._rev[k]][0], _KeyCodes[KeyModifier._rev[k]][1])

    spec_key = False
    for c in s:
        a = ord(c)
        if spec_key:
            spec_key = False
            type_char(a)

        elif a == 0:
            spec_key = True
            continue

        elif a >= 0x20 and a <= 0x7E:
            code = win32api.VkKeyScan(c)
            if code & 0x100 != 0 and modifiers is None:
                press_key(_KeyCodes['SHIFT'][0], _KeyCodes['SHIFT'][1])

            type_char(code)

            if code & 0x100 != 0 and modifiers is None:
                release_key(_KeyCodes['SHIFT'][0], _KeyCodes['SHIFT'][1])

        else:
            raise FailExit('unknown symbol \'%s\' in \'%s\'' % (str(c), str(s)))

    if modifiers is not None:
        for k in KeyModifier._rev:
            if modifiers & k != 0:
                release_key(_KeyCodes[KeyModifier._rev[k]][0], _KeyCodes[KeyModifier._rev[k]][1])





class Region(object):

    def __init__(self, *args, **kwargs):  # relation='top-left', title=None):
        '''
        Конструктор области.
            args[0]:
                число              -- координата "x"; строим новую область-прямоуголник
                объект типа Region -- копируем уже имеющуюуся область-прямоуголник
            relation:
                'top-left' -- x,y являются координатам левого верхнего угла области-прямоуголника; область строится от этой точкаи
                'center'   -- x,y являются координатам центра области-прямоуголника; область строится от этой точкаи

            Внутренние поля класса:
                _x, _y  --  левый верхнйи угол; будут проецироваться на x, y
                _w, _h  --  ширина и высота; будут проецироваться на w, h

            Публичные поля класса:
                x, y  --  левый верхнйи угол; будут записываться из _x, _y
                w, h  --  ширина и высота; будут записываться из _w, _h

            Смысл "ширина" и "высота":
                Под этими терминами понимает число пикселей по каждому из измерений, принадлежащих области. "Рамка" тоже входит в область.
                Т.о. нулем эти величины быть не могут. Равенство единице, к примеру, "ширины" означает прямоугольник вырождается в вертикальную линиию
                толщиной в 1 пиксель.

        '''
        self.auto_wait_timeout = 3.0

        (self.x, self.y, self._x, self._y) = (None, None, None, None)
        (self.w, self.h, self._w, self._h) = (None, None, None, None)
        self.title = None

        try:
            if 'title' in kwargs:
                self.title = str(kwargs['title'])
            self.setRect(*args, **kwargs)
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'Region\' class constructor call:\n\targs = %s\n\tkwargs = %s' % (traceback.format_exc(), str(args), str(kwargs)))


    def __str__(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return 'Region (%i, %i, %i, %i)' % (self._x, self._y, self._w, self._h)


    def setX(self, x, relation='top-left'):
        ''' 'top-left' -- x - координата угла; 'center' -- x - координата цента '''
        (self.y, self.w, self.h) = (self._y, self._w, self._h)
        if isinstance(x, int) and relation in RELATIONS:
            if relation == 'top-left':
                self._x = self.x = x
            elif relation == 'center':
                self._x = self.x = x - self._w/2
        else:
            raise FailExit('[error] Incorect \'setX()\' method call:\n\tx = %s\n\trelation = %s' % (str(x), str(relation)))

    def setY(self, y, relation='top-left'):
        ''' 'top-left' -- y - координата угла; 'center' -- у - координата цента '''
        (self.x, self.w, self.h) = (self._x, self._w, self._h)
        if isinstance(y, int) and relation in RELATIONS:
            if relation == 'top-left':
                self._y = self.y = y
            elif relation == 'center':
                self._y = self.y = y - self._h/2
        else:
            raise FailExit('[error] Incorect \'setY()\' method call:\n\ty = %s\n\trelation = %s' % (str(y), str(relation)))

    def setW(self, w, relation='top-left'):
        ''' 'top-left' -- не надо менять x; 'center' --  не надо менять x '''
        (self.x, self.y, self.h) = (self._x, self._y, self._h)
        if isinstance(w, int) and w > 0 and relation in RELATIONS:
            self._w = self.w = w
            if relation == 'center':
                self._x = self.x = self._x - w/2
        else:
            raise FailExit('[error] Incorect \'setW()\' method call:\n\tw = %s' % str(w))

    def setH(self, h, relation='top-left'):
        ''' 'top-left' -- не надо менять y; 'center' --  не надо менять y '''
        (self.x, self.y, self.w) = (self._x, self._y, self._w)
        if isinstance(h, int) and h > 0 and relation in RELATIONS:
            self._h = self.h = h
            if relation == 'center':
                self._y = self.y = self._y - h/2
        else:
            raise FailExit('[error] Incorect \'setH()\' method call:\n\th = %s' % str(h))


    def setRect(self, *args, **kwargs):
        try:
            if len(args) == 1 and isinstance(args[0], Region):
                self.__set_from_Region(args[0])

            elif len(args) == 4 and isinstance(args[0], int) and isinstance(args[1], int) and isinstance(args[2], int) and isinstance(args[3], int) and args[2] > 0 and args[3] > 0:
                for a in args:
                    if not isinstance(a, int):
                        raise FailExit('#1')

                if 'relation' in kwargs:
                    if kwargs['relation'] not in RELATIONS:
                        raise FailExit('#2')
                    relation = kwargs['relation']
                else:
                    relation = 'top-left'

                self._w = self.w = args[2]
                self._h = self.h = args[3]
                if relation == 'top-left':
                    self._x = self.x = args[0]
                    self._y = self.y = args[1]
                elif relation == 'center':
                    self._x = self.x = x - args[2]/2
                    self._y = self.y = y - args[3]/2
            else:
                raise FailExit('#3')

        except FailExit as e:
            raise FailExit('[error] Incorect \'setRect()\' method call:\n\targs = %s\n\tkwargs = %s\n\tadditional comment: %s' % (str(args), str(kwargs), str(e)))

    def __set_from_Region(self, reg):
        self._x = self.x = reg.x
        self._y = self.y = reg.y
        self._w = self.w = reg.w
        self._h = self.h = reg.h


    def getX(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return self._x

    def getY(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return self._y

    def getW(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return self._w

    def getH(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return self._h


    def offset(self, *args):
        ''' Возвращает область, сдвинутую, относительно self.
            Вериант №1 (как в Sikuli):
                loc_offs := args[0]  --  тип Location; на сколько сдвинуть; (w,h) сохраняется
            Вериант №2:
                x_offs := args[0]  --  тип int; на сколько сдвинуть; w сохраняется
                y_offs := args[1]  --  тип int; на сколько сдвинуть; h сохраняется
        '''
        if len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], int):
            return Region(self._x + args[0], self._y + args[1], self._w, self._h)
        elif len(args) == 1 and isinstance(args[0], Location):
            return Region(self._x + args[0]._x, self._y + args[0]._y, self._w, self._h)
        else:
            raise FailExit('[error] Incorect \'offset()\' method call:\n\targs = %s' % str(args))

    def right(self, l=None):
        ''' Возвращает область справа от self. Self не включено. Высота новой области совпадает с self. Длина новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
                #scr = Screen(_scr_num_of_point(self._x, self._y))
                scr = Screen('virt')
                reg = Region(self._x + self._w, self._y, (scr.x + scr.w - 1) - (self._x + self._w) + 1, self._h)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x + self._w, self._y, l, self._h)
            # elif isinstance(l, Region):  --  TODO: до пересечения с ... Если внутри или снаружи.
            else:
                raise FailExit('type of \'l\' is %s; l = %s', (str(type(l)), str(l)))
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'right()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        return reg

    def left(self, l=None):
        ''' Возвращает область слева от self. Self не включено. Высота новой области совпадает с self. Длина новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
                #scr = Screen(_scr_num_of_point(self._x, self._y))
                scr = Screen('virt')
                reg = Region(scr.x, self._y, (self._x - 1) - scr.x + 1, self._h)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x - l, self._y, l, self._h)
            # elif isinstance(l, Region):  --  TODO: до пересечения с ... Если внутри или снаружи.
            else:
                raise FailExit()
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'left()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        return reg

    def above(self, l=None):
        ''' Возвращает область сверху от self. Self не включено. Ширина новой области совпадает с self. Высота новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
                #scr = Screen(_scr_num_of_point(self._x, self._y))
                scr = Screen('virt')
                reg = Region(self._x, scr.y, self._w, (self._y - 1) - scr.y + 1)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x, self._y - l, self._w, l)
            # elif isinstance(l, Region):  --  TODO: до пересечения с ... Если внутри или снаружи.
            else:
                raise FailExit()
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'above()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        return reg

    def below(self, l=None):
        ''' Возвращает область снизу от self. Self не включено. Ширина новой области совпадает с self. Высота новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
                #scr = Screen(_scr_num_of_point(self._x, self._y))
                scr = Screen('virt')
                reg = Region(self._x, self._y + self._h, self._w, (scr.y + scr.h - 1) - (self._y + self._h) + 1)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x, self._y + self._h, self._w, l)
            # elif isinstance(l, Region):  --  TODO: до пересечения с ... Если внутри или снаружи.
            else:
                raise FailExit()
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'below()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        return reg


    def getTopLeft(self):
        return Location(self._x, self._y)

    def getTopRight(self):
        return Location(self._x, self._y + self._w - 1)

    def getBottomLeft(self):
        return Location(self._x + self._h - 1, self._y)

    def getBottomRight(self):
        return Location(self._x + self._h - 1, self._y + self._w - 1)

    def getCenter(self):
        return Location(self._x + self._w/2, self._y + self._h/2)


    def __get_field_for_find(self):
        return _grab_screen(self._x, self._y, self._w, self._h)

    def __find(self, ps, field):
        CF = 0
        if CF == 0:
            res = cv2.matchTemplate(field, ps._cv2_pattern, cv2.TM_CCORR_NORMED)
            loc = np.where(res > ps.getSimilarity())  # 0.995
        elif CF == 1:
            res = cv2.matchTemplate(field, ps._cv2_pattern, cv2.TM_SQDIFF_NORMED)
            loc = np.where(res < 1.0 - ps.getSimilarity())  # 0.005

        # for pt in zip(*loc[::-1]):
        #    cv2.rectangle(field, pt, (pt[0] + self._w, pt[1] + self._h), (0, 0, 255), 2)
        # cv2.imshow('field', field)
        # cv2.imshow('pattern', ps._cv2_pattern)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        # 'res' -- Матрица, где каждый элемент содержит корреляуию кусочка "поля" с шаблоном. Каждый элемент
        #          матрицы соответствует пикселю из "поля". Индексация, вестимо, от нуля.
        # 'loc' -- структура вида (array([264, 284, 304]), array([537, 537, 537])) где три пары индексов элементов матрицы 'res',
        #          для которых выполняется условие. Если из zip'нуть, то получиться [(264, 537), (284, 537), (304, 537)].
        # Т.о. каждый tuple в zip'е ниже будет иметь три элемента: индекс по 'x', индекс по 'y' и 'score'.

        '''x_arr = map(lambda x: int(x) + self._x, loc[1])
        y_arr = map(lambda y: int(y) + self._y, loc[0])
        s_arr = map(lambda s: float(s), res[loc[0], loc[1]])
        return zip(x_arr, y_arr, s_arr)'''
        return map(lambda x, y, s: (int(x) + self._x, int(y) + self._y, float(s)), loc[1], loc[0], res[loc[0], loc[1]])


    def findAll(self, ps):
        try:
            if isinstance(ps, str):
                ps = Pattern(ps)
            if not isinstance(ps, Pattern):
                raise FailExit('bad \'ps\' argument; it should be a string (path to image file) or \'Pattern\' object')

            pts = self.__find(ps, self.__get_field_for_find())
            return map(lambda pt: Match(pt[0], pt[1], ps._w, ps._h, pt[2], ps.getFilename()), pts)

        except FailExit as e:
            raise FailExit('[error] Incorect \'findAll()\' method call:\n\tps = %s\n\tadditional comment: %s' % (str(ps), str(e)))


    def _wait_for_appear_or_vanish(self, ps, timeout, aov):
        if isinstance(ps, str):
            ps = Pattern(ps)
        if not isinstance(ps, Pattern):
            raise FailExit('bad \'ps\' argument; it should be a string (path to image file) or \'Pattern\' object')
        if timeout is None:
            timeout = self.auto_wait_timeout
        if not ( (isinstance(timeout, float) or isinstance(timeout, int)) and timeout >= 0 ):
            raise FailExit('bad \'timeout\' argument')

        prev_field = None
        elaps_time = 0
        while True:
            field = self.__get_field_for_find()

            if prev_field is None or (prev_field != field).all():
                pts = self.__find(ps, field)

                if aov == 'appear':
                    if len(pts) != 0:
                        # Что-то нашли. Выреме один вариант с лучшим 'score'. Из несольких с одинаковыми 'score' будет первый при построчном проходе по экрану.
                        pt = max(pts, key=lambda pt: pt[2])
                        return Match(pt[0], pt[1], ps._w, ps._h, pt[2], ps.getFilename())

                elif aov == 'vanish':
                    if len(pts) == 0:
                        return

                else:
                    raise FailExit('unknown \'aov\' = \'%s\'' % str(aov))

            time.sleep(DELAY_BETWEEN_CV_ATTEMPT)
            elaps_time += DELAY_BETWEEN_CV_ATTEMPT
            if elaps_time >= timeout:
                raise FindFailed()


    def find(self, ps, timeout=None):
        ''' Ждет, пока паттерн не появится. timeout может быть положительным числом или None. timeout = 0 означает однократную проверку; None -- использование дефолтного значения.
        Возвращает Region, если паттерн появился, и исключение FindFailed, если нет. '''
        try:
            reg = self._wait_for_appear_or_vanish(ps, timeout, 'appear')
        except FailExit as e:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'find()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
        else:
            return reg

    def waitVanish(self, ps, timeout=None):
        ''' Ждет, пока паттерн не исчезнет. Если паттерна уже не было к началу выполнения процедуры, то завершается успешно.
        timeout может быть положительным числом или None. timeout = 0 означает однократную проверку; None -- использование дефолтного значения.'''
        try:
            self._wait_for_appear_or_vanish(ps, timeout, 'vanish')
        except FailExit as e:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'waitVanish()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
        except FindFailed:
            return False
        else:
            return True


    def exists(self, ps):
        try:
            self._wait_for_appear_or_vanish(ps, 0, 'appear')
        except FailExit as e:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'exists()\' method call:\n\tself = %s\n\tps = %s' % (traceback.format_exc(), str(self), str(ps)))
        except FindFailed:
            return False
        else:
            return True


    def wait(self, ps=None, timeout=None):
        ''' Для совместимости с Sikuli. Ждет появления паттерна или просто ждет.
        timeout может быть положительным числом или None. timeout = 0 означает однократную проверку; None -- использование дефолтного значения.'''
        if ps is None:
            if timeout is not None:
                time.sleep(timeout)
        else:
            try:
                reg = self._wait_for_appear_or_vanish(ps, timeout, 'appear')
            except FailExit as e:
                raise FailExit('\nNew stage of %s\n[error] Incorect \'wait()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
            else:
                return reg


    def setAutoWaitTimeout(self, timeout):
        if (isinstance(timeout, float) or isinstance(timeout, int)) and timeout >= 0:
            self.auto_wait_timeout = timeout
        else:
            raise FailExit('[error] Incorect \'setAutoWaitTimeout()\' method call:\n\ttimeout = %s' % str(timeout))


    def click(self):
        self.getCenter().click()

    def doubleClick(self):
        self.getCenter().doubleClick()

    def type(self, text, m = None, click = True):
        ''' Не как в Sikuli '''
        self.getCenter().type(text, m, click)

    def enter_text(self, text):
        ''' Не как в Sikuli '''
        self.getCenter().enter_text(text)



class Screen(Region):
    ''' Экран.

        x, y  --  координаты левого верхнего угла в системе координат виртуального рабочего стола
        w, h  --  размеры прямоуголника экрана
    '''
    def __init__(self, n):
        if n == 'virt':
            n = 0

        if isinstance(n, int) and n >= 0:
            # Returns a sequence of tuples. For each monitor found, returns a handle to the monitor, device context handle, and intersection rectangle: (hMonitor, hdcMonitor, PyRECT)
            (mon_hndl, _, mon_rect) = _screen_n_to_mon_descript(n)

            super(Screen, self).__init__(mon_rect[0], mon_rect[1], mon_rect[2]-mon_rect[0], mon_rect[3]-mon_rect[1], title='Screen (%i)' % n)
            self.n = self._n = n
            self.__mon_hndl = mon_hndl

        else:
            raise FailExit()

    def __str__(self):
        super(Screen, self).__str__()
        self.n = self._n
        return 'Screen (%i) (%i, %i, %i, %i)' % (self._n, self._x, self._y, self._w, self._h)



class Match(Region):
    def __init__(self, x, y, w, h, score, img_path):
        try:
            super(Match, self).__init__(x, y, w, h)
            if not isinstance(score, float) or score <= 0.0 or score > 1.0:
                raise FailExit('not isinstance(score, float) or score <= 0.0 or score > 1.0:')
            self.__score = score
            self._img_path = img_path
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'Match\' constructor call:\n\tx = %s\n\ty = %s\n\tw = %s\n\th = %s\n\tscore = %s\n\t' % (traceback.format_exc(), str(w), str(y), str(w), str(h), str(score)))

    def __str__(self):
        return ('Match of \'%s\' in (%i, %i, %i, %i) with score = %f' % (str(self._img_path), self._x, self._y, self._w, self._h, self.__score))

    def getScore(self):
        ''' Sikuli: Get the similarity score the image or pattern was found. The value is between 0 and 1. '''
        return self.__score

    def getTarget(self):
        ''' Sikuli: Get the 'location' object that will be used as the click point.
        Typically, when no offset was specified by Pattern.targetOffset(), the click point is the center of the matched region.
        If an offset was given, the click point is the offset relative to the center. '''
        raise Exception('TODO here')


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

    def mouseMove(self):
        win32api.SetCursorPos((self.x, self.y))
        time.sleep(DELAY_AFTER_MOUSE_MOVEMENT)

    def click(self):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)

    def doubleClick(self):
        self.mouseMove()
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)
        time.sleep(DELAY_MOUSE_DOUBLE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, self.x, self.y, 0, 0)
        time.sleep(DELAY_IN_MOUSE_CLICK)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, self.x, self.y, 0, 0)

    def type(self, text, m = None, click = True):
        ''' Не как в Sikuli '''
        if click == True:
            self.click()
        type_text(text, m)

    def enter_text(self, text):
        ''' Не как в Sikuli '''
        self.click()
        type_text(text + Key.ENTER)



class Pattern(object):
    def __init__(self, img_path, similarity=None):
        (self.__similarity, self.__img_path) = (None, None)

        try:
            path = os.path.abspath(img_path)
            if os.path.exists(path) and os.path.isfile(path):
                self.__img_path = path
            else:
                for path in Settings.listImagePath():
                    path = os.path.join(path, img_path)
                    if os.path.exists(path) and os.path.isfile(path):
                        self.__img_path = path
                        break
            if self.__img_path is None:
                raise FailExit('image file not found')


            if similarity is None:
                self.__similarity = Settings.MinSimilarity
            elif isinstance(similarity, float) and similarity > 0.0 and similarity <= 1.0:
                self.__similarity = similarity
            else:
                raise FailExit('error around \'similarity\' parameter')

        except FailExit as e:
            raise FailExit('[error] Incorect \'Pattern\' class constructor call:\n\timg_path = %s\n\tabspath(img_path) = %s\n\tsimilarity = %s\n\tadditional comment: -{ %s }-' % (str(img_path), str(self.__img_path), str(similarity), str(e)))

        self._cv2_pattern = cv2.imread(self.__img_path)
        self.w = self._w = int(self._cv2_pattern.shape[1])
        self.h = self._h = int(self._cv2_pattern.shape[0])

    def __str__(self):
        return 'Pattern of \'%s\' with similarity = %f' % (self.__img_path, self.__similarity)

    def similar(self, similarity):
        return Pattern(self.__img_path, similarity)

    def exact(self):
        return Pattern(self.__img_path, 1.0)

    def getFilename(self):
        return self.__img_path

    def getSimilarity(self):
        return self.__similarity

    def getW(self):
        (self.w, self.h) = (self._w, self._h)
        return self._w

    def getH(self):
        (self.w, self.h) = (self._w, self._h)
        return self._h







# find = sikuli.find  --  будут возвращать неправильные классы если так переопределить
# findAll = sikuli.findAll
# wait = sikuli.wait
