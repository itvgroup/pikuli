# -*- coding: utf-8 -*-

'''
   Файл содержит вспомогательные функции, используемые в pikuli.
'''
import os
import time
import logging
import mss
from io import BytesIO
from PIL import Image

if os.name == 'nt':
    import win32api
    import win32gui
    import win32con

import numpy as np

import pikuli
from ._exceptions import FailExit, FindFailed
from pikuli import logger


# Константа отсутствует в win32con, но есть в http://userpages.umbc.edu/~squire/download/WinGDI.h:
CAPTUREBLT = 0x40000000


def verify_timeout_argument(timeout, allow_None=False, err_msg='pikuli.verify_timeout_argument()'):
    if timeout is None and allow_None:
        return None
    try:
        timeout = float(timeout)
        if timeout < 0:
            raise ValueError
    except (ValueError, TypeError) as ex:
        raise FailExit('%s: wrong timeout = \'%s\' (%s)' % (str(err_msg), str(timeout), str(ex)))
    return timeout


def addImagePath(path):
    pikuli.Settings.addImagePath(path)

def get_hwnd_by_location(x, y):
    '''
    Вернет handle окна с координатами x, y
    '''
    return win32gui.WindowFromPoint((x, y))

def setFindFailedDir(path):
    pikuli.Settings.setFindFailedDir(path)

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


def highlight_region(x, y, w, h, delay=0.5):
    def _cp_boundary(dest_dc, dest_x0, dest_y0, src_dc, src_x0, src_y0, w, h):
        win32gui.BitBlt(dest_dc, dest_x0+0,   dest_y0+0,   w,   1,   src_dc, src_x0,     src_y0,     win32con.SRCCOPY)
        win32gui.BitBlt(dest_dc, dest_x0+0,   dest_y0+h-1, w,   1,   src_dc, src_x0,     src_y0+h-1, win32con.SRCCOPY)
        win32gui.BitBlt(dest_dc, dest_x0+0,   dest_y0+1,   1,   h-2, src_dc, src_x0,     src_y0,     win32con.SRCCOPY)
        win32gui.BitBlt(dest_dc, dest_x0+w-1, dest_y0+1,   1,   h-2, src_dc, src_x0+w-1, src_y0,     win32con.SRCCOPY)

    def _thread_function(x, y, w, h, delay):
        [x, y, w, h] = map(int, [x, y, w, h])
        delay = float(delay)

        # Получим контекст всех дисплев или всего рабочего стола:
        #scr_hdc = win32gui.GetDC(0)
        scr_hdc = win32gui.CreateDC('DISPLAY', None, None)

        mem_hdc = win32gui.CreateCompatibleDC(scr_hdc)  # New context of memory device. This one is compatible with 'scr_hdc'
        new_bitmap_h = win32gui.CreateCompatibleBitmap(scr_hdc, w+2, h+2)
        win32gui.SelectObject(mem_hdc, new_bitmap_h)    # Returns 'old_bitmap_h'. It will be deleted automatically.

        # Сохраняем рамочку в 1 пиксель (она вокруг области (x,y,w,h)):
        _cp_boundary(mem_hdc, 0, 0, scr_hdc, x-1, y-1, w+2, h+2)

        # Рисуем подсветку области:
        # brush = win32gui.CreateSolidBrush(win32api.RGB(255,0,0))
        win32gui.SelectObject(scr_hdc, win32gui.GetStockObject(win32con.NULL_BRUSH))
        pen = win32gui.CreatePen(win32con.PS_DOT, 1, win32api.RGB(148, 0, 0))
        win32gui.SelectObject(scr_hdc, pen)
        for i in range(2):
            win32gui.Rectangle(scr_hdc, x-1, y-1, x+w+1, y+h+1)

        # Восстаналиваема рамочку:
        time.sleep(delay)
        _cp_boundary(scr_hdc, x-1, y-1, mem_hdc, 0, 0, w+2, h+2)

        #win32gui.ReleaseDC(scr_hdc, 0)
        win32gui.DeleteDC(scr_hdc)
        win32gui.DeleteDC(mem_hdc)
        win32gui.DeleteObject(new_bitmap_h)

        # TODO: send redraw signal

    #threading.Thread(target=_thread_function, args=(x, y, w, h, delay), name='highlight_region %s' % str((x, y, w, h, delay))).start()
    return


def _take_screenshot(x, y, w, h, hwnd=None):
    '''
    Получаем скриншот области:
        x, y  --  верхний левый угол прямоуголника в системе координат виртуального рабочего стола
        w, h  --  размеры прямоуголника
    #
    '''
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        max_x = monitor["width"]
        max_y = monitor["height"]
        # проверка выхода заданного значения width за допустимый диапозон
        w = w if x + w < max_x else max_x - x
        # проверка выхода заданного значения height за допустимый диапозон
        h = h if y + h < max_y else max_y - y
        sct_img = sct.grab(dict(left=x, top=y, height=h, width=w))
        scr = mss.tools.to_png(sct_img.rgb, sct_img.size, output="")
        return np.array(Image.open(BytesIO(scr)).convert('RGB'))


"""def _scr_num_of_point(x, y):
    ''' Вернет номер (от нуля) того экрана, на котором располоржен левый верхний угол текущего Region. '''
    m_tl = win32api.MonitorFromPoint((x, y), win32con.MONITOR_DEFAULTTONULL)
    if m_tl is None:
        raise FailExit('top-left corner of the Region is out of visible area of sreens (%s, %s)' % (str(x), str(y)))
    return _monitor_hndl_to_screen_n(m_tl)"""

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


def pixel_color_at(x, y, monitor_number=1):
    return pixels_colors_at([(x, y)], monitor_number)[0]


def pixels_colors_at(coords_tuple_list, monitor_number=1):
    with mss.mss() as sct:
        sct_img = sct.grab(sct.monitors[monitor_number])  # некст по умолчанию выводится на первый монитор
        return list(map(lambda coord: sct_img.pixel(*coord), coords_tuple_list))
