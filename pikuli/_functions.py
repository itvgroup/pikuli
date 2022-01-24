# -*- coding: utf-8 -*-

'''
   Файл содержит вспомогательные функции, используемые в pikuli.
'''
from distutils import extension
import os
import time
import logging
from typing import Any

import mss
from PIL import Image

if os.name == 'nt':
    import win32api
    import win32gui
    import win32con

from .geom.simple_types import Rectangle
from . import FailExit, logger, settings

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
    settings.addImagePath(path)

def get_hwnd_by_location(x, y):
    '''
    Вернет handle окна с координатами x, y
    '''
    return win32gui.WindowFromPoint((x, y))

def setFindFailedDir(path):
    settings.setFindFailedDir(path)

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

class SimpleImage:

    def __init__(self, img_src: Any, pil_img: Image):
        self.img_src = img_src
        self._pil_img = pil_img

    @classmethod
    def from_cv2(cls, img_src: Any, cv2_img):
        return Image.fromarray(cv2_img, mode="RGB")

    @property
    def pillow_img(self) -> Image:
        return self._pil_img

    def save(self, filename, loglevel=logging.DEBUG):
        path = os.path.abspath(filename)
        logger.log(loglevel, f'Save {self.img_src} to {path}')
        
        dir_path = os.path.dirname(path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        _, extension = os.path.splitext(path)
        self._pil_img.save(path, format=extension.lstrip('.'))

def take_screenshot(rect: Rectangle) -> SimpleImage:
    '''
    Получаем скриншот области:
        x, y  --  верхний левый угол прямоуголника в системе координат виртуального рабочего стола
        w, h  --  размеры прямоуголника

    # TODO: Fix multi-monitor configuration!!!
    '''
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        max_x = monitor["width"]
        max_y = monitor["height"]
        # проверка выхода заданного значения width за допустимый диапозон
        w = rect.w if rect.x + rect.w < max_x else max_x - rect.x
        # проверка выхода заданного значения height за допустимый диапозон
        h = rect.h if rect.y + rect.h < max_y else max_y - rect.y
        sct_img = sct.grab(dict(left=rect.x, top=rect.y, height=h, width=w))
        pil_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    return SimpleImage(rect, pil_img)

def pixel_color_at(x, y, monitor_number=1):
    return pixels_colors_at([(x, y)], monitor_number)[0]

def pixels_colors_at(coords_tuple_list, monitor_number=1):
    with mss.mss() as sct:
        sct_img = sct.grab(sct.monitors[monitor_number])  # некст по умолчанию выводится на первый монитор
        return list(map(lambda coord: sct_img.pixel(*coord), coords_tuple_list))
