# -*- coding: utf-8 -*-

''' Субмодуль работы с WinForms через win32api. '''

import psutil
import types
import sys
from win32api import *
from win32gui import *
from win32process import *
from win32con import *

from ctypes import oledll
from ctypes import byref
import comtypes
import comtypes.client

comtypes.client.GetModule('oleacc.dll')             # Что-то там нагенерирует ...
from comtypes.gen.Accessibility import IAccessible  # ... и теперь чать этого импортируем

from pikuli import Region
from _functions import p2c
from _exceptions import *

'''
!!! TODO: !!!
    --- добавить метод првоерки того, что одно окно является прямым, но не обязательно непосредственным продиетелм/потомком другого.
'''

# Тип объекта для запроса AccessibleObjectFromWindow(...):
OBJID_CLIENT   = 0xFFFFFFFC  # + Определяет и даже позволяет переклчюать чекбокс через accDoDefaultAction() +

# Состояние WinForms-checkbox:
UNCHECKED         = 0x100000
CHECKED           = 0x100010  # + +
UNCHECKED_FOCUSED = 0x100004  # focused -- когда выбран в рамочку для изменения с клавиатуры
CHECKED_FOCUSED   = 0x100014


# Словарь "системых" title'ов. Если title не строка, а число отсюда, то title интерпретируется не просто как заголвок окна или текст лейбла, а как указание на какой-то объект.
SYS_TITLES = {'main_window': 0}


def _hwnd2wf(hwnd):
    return WindowsForm(hwnd)


def _hwnd2reg(hwnd, title=None):
    # полчение размеров клменскй области окна
    (_, _, wc, hc) = GetClientRect(hwnd)
    # получение координат левого верхнего угла клиенской области осносительно угла экрана
    (xc, yc) = ClientToScreen(hwnd, (0, 0) )
    return Region(xc, yc, wc, hc)


def _is_visible(hwnd0):
    ''' Определяет свойство visible окна hwnd, а также проверяет наследвоание этого свойства от всех родительских окон. '''
    def _iv(hwnd):
        if GetWindowLong(hwnd, GWL_STYLE) & WS_VISIBLE == 0:
            return False
        if hwnd != 0:
            return iv(GetParent(hwnd))
        return True

    return iv(hwnd0)



class WindowsForm(object):
    '''
    Доступные поля:
        proc_name      --  имя процесса (exe-файла), которому принадлежит окно
        pid            --  PID процесса, которому принадлежит окно
        hwnd           --  win32 указатель на искомое окно
        hwnd_main_win  --  win32 указатель главное окно процесса (самое родительское для искомого)
        title          --  заголовок искомого окна (для кнопок/чек-боксов/т.п. -- это их надписи)
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
            def EnumChildWindows_callback(hwnd, extra):
                if extra['hwnd'] == hwnd:
                    extra['res'] = True

            extra = {'hwnd': hwnd, 'res': False}
            EnumChildWindows(self.hwnd_main_win, EnumChildWindows_callback, extra)
            if not extra['res']:
                raise Exception('pikuli: winforms: constructor error: hwnd = %s is not child for main window %s' % (str(hwnd), str(self.hwnd_main_win)))

        else:
            # raise Exception('pikuli: winforms: constructor error; proc_name = \'%s\', parent = %s' % (str(proc_name), str(parent)))
            raise Exception('pikuli: winforms: constructor error; args = %s' % str(args))

        self.title = GetWindowText(self.hwnd)
        self.class_name = GetClassName(self.hwnd)


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
            raise Exception('pikuli: winforms: can not find process of \'%s\'' % str(self.proc_name))

        EnumWindows(EnumWindows_callback, extra)
        if 'hwnd_main_win' not in extra:
            raise Exception('pikuli: winforms: can not find the window with %s in title of the process \'%s\' (%s)' % (str(self.main_wnd_in_title), str(self.proc_name), str(self.pid)))

        self.pid = extra['pid']
        self.hwnd = extra['hwnd_main_win']
        self.hwnd_main_win = extra['hwnd_main_win']


    def find(self, win_class, title, title_regexp=False, return_list=False):
        '''
        Поиск дочернего окна-объекта любого уровня вложенности. Под окном пнимается любой WinForms-элемент любого класса.
            win_class     --  Искомое окно должно обладать таким WinForms-классом.
            title         --  Искомое окно должно иметь такой заголвоок (текст); в точности такое или это регулярное выражение, в зависимости от флага title_regexp.
            title_regexp  --  В title передается регулярное выржение для поиска.
            return_list   --  Если True, то возвращается список найденных окон. Если False, то возвращается только одно значение или происходит Exception, если найдено несколько элементов.
        Возвращает объект типа Region.
        '''

        if isinstance(title, int) and title in SYS_TITLES.values():
            # Поиск специальных окон, пречисленных в SYS_TITLES.
            if title == SYS_TITLES['main_window']:
                # Поиск главного окна программы:
                if _is_visible(self.hwnd_main_win):
                    return _hwnd2reg(self.hwnd_main_win, GetWindowText(self.hwnd_main_win))
                else:
                    raise FindFailed('pikuli: winforms: find: main window has visible = False.' % (hex(self.hwnd_main_win), str(win_class), str(title)))
            else:
                raise Exception('pikuli: winforms: find: title = \'%s\' not in SYS_TITLES = %s (win_class = \'%s\')' % (str(title), str(SYS_TITLES), str(win_class)))

        elif isinstance(title, str):
            # Поиск окна по его title.
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
                raise FindFailed('pikuli: winforms: find: not win_class = \'%s\' and title = \'%s\' was found.' % (str(win_class), str(title)))

            if return_list:
                return [_hwnd2reg(h, GetWindowText(h)) for h in extra['hwnds'] if _is_visible(h)]
            else:
                if len(extra['hwnds']) == 1:
                    if _is_visible(self.hwnd_main_win):
                        return _hwnd2reg(extra['hwnds'][0], GetWindowText(extra['hwnds'][0]))
                    else:
                        raise FindFailed('pikuli: winforms: find: window %s with win_class = \'%s\' and title = \'%s\' has visible = False.' % (hex(extra['hwnds'][0]), str(win_class), str(title)))
                else:
                    raise Exception('pikuli: winforms: find: more than one elemnt was found with win_class = \'%s\' and title = \'%s\': extra[\'hwnds\'] = %s' % (str(win_class), str(title), str(extra['hwnds'])))

        else:
            raise Exception('pikuli: winforms: find: wrond title = \'%s\' (win_class = \'%s\')' % (str(title), str(win_class)))


    def reg(self):
        ''' Возвращает Region для self-элемента WindowsForm. '''
        return _hwnd2reg(self.hwnd, self.title)

    def bring_to_front(self):
        try:
            SetForegroundWindow(self.hwnd)
            return True
        except Exception as ex:
            p2c('bring_to_front: %s' % str(ex))
            return False

    def is_visible(self):
        ''' Определяет свойство visible искомого окна, а также проверяет наследвоание этого свойства от всех родительских окон. '''
        return _is_visible(self.hwnd)

    def is_button_checked(self):
        '''
        Возвращает True, если кнопка нажата, чек-бокс выбран. В противном случае возвращает False.
        Умеет работать с класическим GDI-контролом и WindowsForms.

        Полезные ссылки по теме WindowsForms:
            https://github.com/phuslu/pyMSAA/blob/27250185fb27488ea9a914249b362d3a8b849d0e/comtypes/test/test_QueryService.py
            http://stackoverflow.com/questions/29392625/check-if-a-winform-checkbox-is-checked-through-winapi-only
            http://stackoverflow.com/questions/34008389/using-accessibleobjectfromwindow-in-python-on-microsoft-word-instance
            http://stackoverflow.com/questions/33901597/getting-last-opened-ms-word-document-object
        '''
        if 'button' not in self.class_name.lower():
            raise Exception('pikuli: winforms: is_button_checked: hwnd = %s with ClassName = \'%s\' seems not to be a \'button\'' % (hex(self.hwnd), hex(self.class_name)))

        if 'windowsforms' in self.class_name.lower():
            obj = comtypes.POINTER(IAccessible)()
            oledll.oleacc.AccessibleObjectFromWindow(self.hwnd, OBJID_CLIENT, byref(obj._iid_), byref(obj))
            state = obj.accState()
            if state == CHECKED or state == CHECKED_FOCUSED:
                return True
            elif state == UNCHECKED or state == UNCHECKED_FOCUSED:
                return False
            else:
                raise Exception('pikuli: winforms: is_button_checked: unknown WinForms state = %s of hwnd = %s' % (hex(state), hex(self.hwnd)))
        else:
            return bool(SendMessage(self.hwnd, BM_GETCHECK, 0, 0))
