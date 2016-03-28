# -*- coding: utf-8 -*-

'''
   Файл содержит вспомогательные функции, используемые в Pikuli.
'''
import pikuli

import sys
import win32con
import win32api
import win32gui
import win32ui
import win32clipboard
import time
import numpy as np


from ._exceptions import FailExit



DELAY_KBD_KEY_PRESS = 0.020


def p2c(*msgs):
    try:
        addgap = ''
        for m in msgs:
            sys.__stdout__.write('*** ' + addgap + str(m) + '\n')
        sys.__stdout__.flush()
    except Exception as ex:
        print('[warn] error in function \'p2c\': %s' % str(ex))
        print(' '.join(map(str, msgs)))


def wait_while(f_logic, timeout):
    DELAY_BETWEEN_ATTEMTS = 0.5
    elaps_time = 0
    while f_logic():
        if timeout is not None and elaps_time > timeout:
            return False
        time.sleep(DELAY_BETWEEN_ATTEMTS)
        elaps_time += DELAY_BETWEEN_ATTEMTS
    return True


def wait_while_not(f_logic, timeout):
    DELAY_BETWEEN_ATTEMTS = 0.5
    elaps_time = 0
    while not f_logic():
        if timeout is not None and elaps_time > timeout:
            return False
        time.sleep(DELAY_BETWEEN_ATTEMTS)
        elaps_time += DELAY_BETWEEN_ATTEMTS
    return True


def addImagePath(path):
    pikuli.Settings.addImagePath(path)


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


def highlight_region(x, y, w, h):
    area = win32gui.GetDC(0)
    # brush = win32gui.CreateSolidBrush(win32api.RGB(255,0,0))
    win32gui.SelectObject(area, win32gui.GetStockObject(win32con.NULL_BRUSH))
    pen = win32gui.CreatePen(win32con.PS_DOT, 1, win32api.RGB(148, 0, 0))
    win32gui.SelectObject(area, pen)
    for i in range(1, 2):
        win32gui.Rectangle(area, int(x) - 1, int(y) - 1, int(x) + int(w) + 1, int(y) + int(h) + 1)


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


def get_text_from_clipboard():
    win32clipboard.OpenClipboard()
    try:
        data = win32clipboard.GetClipboardData()
    except Exception as ex:
        p2c(str(ex.message))
        data = ''
    win32clipboard.CloseClipboard()
    return data


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
    ''' VirtualCode'ы клавиш клавиатуры, которые рассматриваются как модифкаторы нажатия других клавиш. '''
    # (bVk, bScan_press, bScan_relaese) скан коды для XT-клавиатуры. Но они могут быть многобайтовыми. Поэтому мока пробуем передавать вместо них нули.
    'ALT':   (win32con.VK_MENU, 0, 0),
    'CTRL':  (win32con.VK_CONTROL, 0, 0),
    'SHIFT': (win32con.VK_SHIFT, 0, 0),
}


class KeyModifier(object):
    '''
    Битовые маски модификаторов. С их помощью будет парсится аргумент modifiers функции type_text()
        ALT   = 0x01
        CTRL  = 0x02
        SHIFT = 0x04
        _rev  = {0x01: 'ALT', 0x02: 'CTRL', 0x04: 'SHIFT'}
    '''
    _rev = {}
for (m, i) in (lambda l: zip(l, range(len(l))))(['ALT', 'CTRL', 'SHIFT']):
    setattr(KeyModifier, m, 2**i)
    KeyModifier._rev[getattr(KeyModifier, m)] = m


class Key(object):
    '''
    Ноль-символ и VirtualCode специальных клавиш. Именно такую пару можно вставлять прямо в текстовую
    строку, подаваемую на вход type_text(). Ноль-символ говорит о том, что за ним идет не литера, а коды
    специальной клавиши.

    https://msdn.microsoft.com/en-us/library/windows/desktop/dd375731(v=vs.85).aspx ("MSDN: Virtual-Key Codes")
    '''
    ENTER      = chr(0) + chr(win32con.VK_RETURN)
    ESC        = chr(0) + chr(win32con.VK_ESCAPE)
    TAB        = chr(0) + chr(win32con.VK_TAB)
    LEFT       = chr(0) + chr(win32con.VK_LEFT)
    UP         = chr(0) + chr(win32con.VK_UP)
    RIGHT      = chr(0) + chr(win32con.VK_RIGHT)
    DOWN       = chr(0) + chr(win32con.VK_DOWN)
    PAGE_UP    = chr(0) + chr(win32con.VK_PRIOR)
    PAGE_DOWN  = chr(0) + chr(win32con.VK_NEXT)
    BACKSPACE  = chr(0) + chr(win32con.VK_BACK)


def type_text(s, modifiers=None):
    '''
    Особенности:
        -- Если установлены modifiers, то не будет различия между строчными и загалвными буксами.
           Т.е., будет игнорироваться необходимость нажимать Shift, если есть заглавные символы.
    '''
    # https://mail.python.org/pipermail/python-win32/2013-July/012862.html
    # https://msdn.microsoft.com/ru-ru/library/windows/desktop/ms646304(v=vs.85).aspx ("MSDN: keybd_event function")
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

    s = str(s)

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

