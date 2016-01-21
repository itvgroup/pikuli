# -*- coding: utf-8 -*-

''' Субмодуль работы с WinForms через win32api. '''

import psutil
import types

from win32api import *
from win32gui import *
from win32process import *
from win32con import *

from pikuli import Region


class FindFailed(Exception):
    pass


def _hwnd2wf(hwnd):
    return WindowsForm(hwnd)


def _hwnd2reg(hwnd, title=None):
    (left, top, right, bottom) = GetWindowRect(hwnd)
    return Region(left, top, right-left, bottom-top)


class WindowsForm(object):
    '''
    Доступные поля:
        proc_name
        pid
        hwnd
        hwnd_main_win
        title
    '''

    def __init__(self, *args):  # proc_name=None, in_title=None, parent=None, hwnd=None):
        '''
        Вариант №1 (новый экземпляр класса для главного окна):
            args[0]: proc_name  --  указывается явно только при создании класса для всего окна. Если класс создатся для элемента окна, то этот параметр копируется.
            args[1]: in_title   --  список строк, которые должны встречаться в заголовке окна.

        Вариант №2 (экземпляр класса для какого-либо элемента главного окна):
            args[0]: hwnd       --  hwnd этого элемента окна.
        '''
        # if proc_name is not None and in_title is not None and parent is None and hwnd is None:
        if len(args) == 2 and isinstance(args[0], types.StringType) and (isinstance(args[1], types.StringType) or isinstance(args[1], types.ListType)):
            self.proc_name = args[0]
            self.pid = None
            self.hwnd = None
            self.hwnd_main_win = None

            if not isinstance(args[1], types.ListType):
                self.main_wnd_in_title = [args[1]]
            else:
                self.main_wnd_in_title = args[1]
            self._get_main_window_hwnd()

        # elif parent is not None and hwnd is not None and proc_name is None and in_title is None:
        elif len(args) == 1 and (isinstance(args[0], types.IntType) or isinstance(args[0], types.LongType)):
            self.proc_name = parent.proc_name
            self.pid = parent.pid
            self.hwnd = long(hwnd)
            self.hwnd_main_win = parent.hwnd_main_win

            # Проверим, что дочерний элемент:
            extra = {'hwnd': hwnd, 'res': False}
            def EnumChildWindows_callback(hwnd, extra):
                if extra['hwnd'] == hwnd:
                    extra['res'] = True
            EnumChildWindows(self.hwnd_main_win, EnumChildWindows_callback, extra)
            if not extra['res']:
                raise Exception('pikuli: winforms_operator: constructor error: hwnd = %s is not child for main window %s' % (str(hwnd), str(self.hwnd_main_win)))

        else:
            # raise Exception('pikuli: winforms_operator: constructor error; proc_name = \'%s\', parent = %s' % (str(proc_name), str(parent)))
            raise Exception('pikuli: winforms_operator: constructor error; args = %s' % str(args))

        self.title = GetWindowText(self.hwnd)


    def _get_main_window_hwnd(self):

        def EnumWindows_callback(hwnd, extra):                      # Callback на перебор всех окон.
            (threadId, processId) = GetWindowThreadProcessId(hwnd)  # По указателяю на окно получаем (threadId, processId)
            if processId == extra['pid']:
                text = GetWindowText(hwnd)
                for elem in self.main_wnd_in_title:
                    if elem not in text:
                        return
                extra['hwnd_main_win'] = long(hwnd)

        extra = None
        for proc in psutil.process_iter():
            if proc.name() == self.proc_name:
                extra = {'pid': proc.pid}
                break
        if extra is None:
            raise Exception('pikuli: winforms_operator: can not find process of \'%s\'' % str(self.proc_name))

        EnumWindows(EnumWindows_callback, extra)
        if 'hwnd_main_win' not in extra:
            raise Exception('pikuli: winforms_operator: can not find the window with %s in title of the process \'%s\' (%s)' % (str(self.main_wnd_in_title), str(self.proc_name), str(self.pid)))

        self.pid = extra['pid']
        self.hwnd = extra['hwnd_main_win']
        self.hwnd_main_win = extra['hwnd_main_win']


    def find(self, win_class, title, title_regexp=False, return_list=False):
        ''' Поиск дочернего окна-объекта любого уровня вложенности. Под окном пнимается любой WinForms-элемент любого класса.
            win_class     --  Искомое окно должно обладать таким WinForms-классом.
            title         --  Искомое окно должно иметь такой заголвоок (текст); в точности такое или это регулярное выражение, в зависимости от флага title_regexp.
            title_regexp  --  В title передается регулярное выржение для поиска.
            return_list   --  Если True, то возвращается список найденных окон. Если False, то возвращается только одно значение или происходит Exception, если найдено несколько элементов. '''

        if title_regexp:
            extra = {'hwnds': [], 're_comp': re.compile(title)}
        else:
            extra = {'hwnds': [], 're_comp': None}

        def EnumChildWindows_callback(hwnd, extra):
            if hwnd == 0:
                return
            if (not title_regexp and title == GetWindowText(hwnd)) or (title_regexp and extra['re_comp'].match(GetWindowText(hwnd))):
                if win_class.lower() in GetClassName(hwnd).lower().split('.'):
                    extra['hwnds'] += [hwnd]
        EnumChildWindows(self.hwnd_main_win, EnumChildWindows_callback, extra)

        if len(extra['hwnds']) == 0:
            raise FindFailed('pikuli: winforms_operator: find: not win_class = \'%s\' and title = \'%s\' was found.' % (str(win_class), str(title)))

        if return_list:
            return [_hwnd2reg(h, GetWindowText(h)) for h in extra['hwnds']]
        else:
            if len(extra['hwnds']) == 1:
                return _hwnd2reg(extra['hwnds'][0], GetWindowText(extra['hwnds'][0]))
            else:
                raise Exception('pikuli: winforms_operator: find: more than one elemnt was found with win_class = \'%s\' and title = \'%s\': extra[\'hwnds\'] = %s' % (str(win_class), str(title), str(extra['hwnds'])))


    def reg(self):
        ''' Возвращает Region для self-элемента WindowsForm. '''
        return _hwnd2reg(self.hwnd, self.title)
