# -*- coding: utf-8 -*-

'''
   Файл содержит вспомогательные функции, используемые в pikuli.
'''
import os
import time
import logging
import os

if os.name == 'nt':
    import win32ui
    import win32api
    import win32gui
    import win32con

import numpy as np

import pikuli
from ._exceptions import FailExit, FindFailed


logger = logging.getLogger('axxon.pikuli')


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
        hwnd  --  Если None, то используется контекст 'DISPLAY'. Если не None, то используется контекст окна с hwnd
                  (если рисовать в контекст дисплея, то не портятся картинки в конетксте окон).

      Любопытно, что если пытаться выйти за пределы левого монитора, читая данные из его контекста, то оставшаяся
    часть скриншота сам будет браться и из контекста другого монитора. Т.о., важно знать какому монитору принадлежит
    верхний левый угол прямоуголника, скриншот которого получаем. И не надо провериять, на каких мониторах располагаются
    остальные углы этой области. Вообще без проблем можно право и вниз уйти за пределы всех мониторов.
      Однако, надо помнить, что при копировании буфера через BitBlt() надо указывать начальные координаты с системе
    отсчета монитора, а не виртуального рабочего стола. Т.о. входные (x,y) надо пересчитывать.
      Еще нюанс: копирование данных из контекста окна дает белый фон на чисто OpenGL'ой раскледке камер. Аналогично
    с windll.user32.PrintWindow(...). Помогает применение флага CAPTUREBLT у BitBlt(...). Но надо еще изучать (TODO here).

      Нужны какие-то новые технологии типа DirectX или DWM, чтоыб наверняка сделать скриншот всего соедрежимого окна с OpenGL.
    '''
    # http://stackoverflow.com/questions/3291167/how-to-make-screen-screenshot-with-win32-in-c
    # http://stackoverflow.com/questions/18733486/python-win32api-bitmap-getbitmapbits
    # http://stackoverflow.com/questions/24129253/screen-capture-with-opencv-and-python-2-7
    # http://vsokovikov.narod.ru/New_MSDN_API/Bitmaps/captur_image.htm
    # http://stackoverflow.com/questions/19695214/python-screenshot-of-inactive-window-printwindow-win32gui  --  скриншот окна
    # https://msdn.microsoft.com/en-us/library/windows/desktop/dd183402(v=vs.85).aspx
    #
    # Как узнать рамер экрана:
    #   Варинат 1:
    #       (_, _, scr_rect) = _screen_n_to_mon_descript(n)
    #       (w, h) = (scr_rect[2] - scr_rect[0], scr_rect[3] - scr_rect[1])
    #   Варинат 2:
    #       w = win32print.GetDeviceCaps(scr_hdc, win32con.HORZRES)
    #       h = win32print.GetDeviceCaps(scr_hdc, win32con.VERTRES)
    #
    x, y, w, h = map(int, (x, y, w, h))
    mpos = list(win32api.GetCursorPos())

    # Получим контекст всех дисплев или всего рабочего стола:
    hwnd = None  # !!! не работает скриншот окна с OpenGL :(
    if hwnd is None:
        #scr_hdc = win32gui.GetDC(0)
        scr_hdc = win32gui.CreateDC('DISPLAY', None, None)
    else:
        scr_hdc = win32gui.GetDC(hwnd)  # Контекст только клиентской части окна! Не вклчаются даже менюшеки типа 'File' и скролл-бары.
        x, y  = win32gui.ScreenToClient(hwnd, (x, y))

    # Спрячем курсо вне эурана: не влияние на интерфейс (подсветка чего-то при наведении), не попадет на скриншот.
    #win32api.SetCursorPos((win32print.GetDeviceCaps(scr_hdc, win32con.HORZRES) + 1, win32print.GetDeviceCaps(scr_hdc, win32con.VERTRES) + 1))

    mem_hdc = win32gui.CreateCompatibleDC(scr_hdc)  # New context of memory device. This one is compatible with 'scr_hdc'
    new_bitmap_h = win32gui.CreateCompatibleBitmap(scr_hdc, w, h)
    win32gui.SelectObject(mem_hdc, new_bitmap_h)    # Returns 'old_bitmap_h'. It will be deleted automatically.

    # Прямое копирование из контекста окна
    win32gui.BitBlt(mem_hdc, 0, 0, w, h, scr_hdc, x, y, win32con.SRCCOPY)  # | CAPTUREBLT)

    bmp = win32ui.CreateBitmapFromHandle(new_bitmap_h)
    bmp_info = bmp.GetInfo()
    if bmp_info['bmHeight'] != h or bmp_info['bmWidth'] != w:
        raise FailExit('bmp_info = %s, but (x, y, w, h, hwnd) = %s' %
                       (str(bmp_info), str((w, y, w, h, hwnd))))
    if bmp_info['bmType'] != 0 or bmp_info['bmPlanes'] != 1:
        raise FailExit('bmp_info = %s: bmType !=0 or bmPlanes != 1; (x, y, w, h, hwnd) = %s' %
                       (str(bmp_info), str((w, y, w, h, hwnd))))
    if bmp_info['bmBitsPixel'] % 8 != 0:
        raise FailExit('bmp_info = %s: (bmBitsPixel mod. 8) != 0; (x, y, w, h, hwnd) = %s' %
                       (str(bmp_info), str((w, y, w, h, hwnd))))

    bmp_arr = list(bmp.GetBitmapBits())
    del bmp_arr[3::4]  # Dele alpha channel. TODO: Is it fast enough???
    bmp_np = np.array(bmp_arr, dtype=np.uint8).reshape((h, w, 3))

    #win32api.SetCursorPos(mpos)  # Возвращаем курсор.
    if hwnd is None:
        win32gui.DeleteDC(scr_hdc)
    else:
        win32gui.ReleaseDC(hwnd, scr_hdc)
    win32gui.DeleteDC(mem_hdc)
    win32gui.DeleteObject(new_bitmap_h)

    # import cv2, time
    # t = time.time()
    # cv2.imwrite('d:\\tmp\\s-%i-%06i-field.png' % (int(t), (t-int(t))*10**6), bmp_np)

    return bmp_np


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
"""
def _take_screenshot_(*args):
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

def pixel_color_at(x, y):
    hdc = win32gui.GetWindowDC(win32gui.GetDesktopWindow())
    c = int(win32gui.GetPixel(hdc, x, y))
    # (r, g, b)
    return (c & 0xff), ((c >> 8) & 0xff), ((c >> 16) & 0xff)
