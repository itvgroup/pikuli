# -*- coding: utf-8 -*-

''' Субмодуль работы с контролами через win32api. '''

import os
import re
import types
import logging

import psutil

from win32api import *
from win32con import *
from win32gui import *
from win32process import *
from win32con import *
from ctypes import oledll
from ctypes import byref
import comtypes
import comtypes.client



import pikuli
from pikuli._exceptions import FindFailed
from pikuli.geom import Region
from pikuli import wait_while, wait_while_not
from pikuli import logger


'''
!!! TODO: !!!
    --- добавить метод првоерки того, что одно окно является прямым, но не обязательно непосредственным продиетелм/потомком другого.
    --- все-таки надо отдельные классы для разных контролов завести
'''

# Тип объекта для запроса AccessibleObjectFromWindow(...):
OBJID_CLIENT = 0xFFFFFFFC  # + Определяет и даже позволяет переклчюать чекбокс через accDoDefaultAction() +

# Состояние WinForms-checkbox:
#   Обычно само значание:
#     UNCHECKED         = 0x100000
#     CHECKED           = 0x100010  # + +
#     UNCHECKED_FOCUSED = 0x100004  # focused -- когда выбран в рамочку для изменения с клавиатуры
#     CHECKED_FOCUSED   = 0x100014
#   Маски:
BUTTON_NOT_MARKED = 0x000001  # Если этот бит в поле state кнопки 0, то текст кнопки красный (к примеру, речь о кнопке Applay)
CHECKED           = 0x000010
FOCUSED           = 0x000004


# # Словарь "системых" title'ов. Если title не строка, а число отсюда, то title интерпретируется не просто как заголвок окна или текст лейбла, а как указание на какой-то объект.
# SYS_TITLES = {'main_window': 0}


def _hwnd2wf(hwnd):
    return HWNDElement(hwnd)


def _is_visible(hwnd0):
    ''' Определяет свойство visible окна hwnd, а также проверяет наследвоание этого свойства от всех родительских окон. '''
    def _iv(hwnd):
        if hwnd == 0:
            return True
        if GetWindowLong(hwnd, GWL_STYLE) & WS_VISIBLE == 0:
            return False
        return _iv(GetParent(hwnd))
    return _iv(hwnd0)


def _find_main_parent_window(child_hwnd, child_pid=None):
    ''' Для указанного (дочеренего) окна ищет самое-самое родительское. Если child_pid=None, то родительским
    будет объявлено то, у кого родитель -- "рабочий стол" (hwnd = 0). Если указан child_pid, то при проверке родительских
    оконо по цепочке будет все время проверять и сохранение PID'а этих окон. Родительским будет объявлено то, у которого
    родитель имеет другой PID (ну, или опять же "рабочий стол").
    Если окно и так самый-самый родитель, то вернется его же собственный hwnd. '''
    def _fmpw(child_hwnd, child_pid):
        parent_hwnd = GetParent(child_hwnd)
        if parent_hwnd == 0:
            return child_hwnd
        else:
            if child_pid is not None:
                (_, ppid) = GetWindowThreadProcessId(parent_hwnd)  # По указателяю на окно получаем (threadId, processId)
                if int(ppid) != int(child_pid):
                    return child_hwnd
        return _fmpw(parent_hwnd, child_pid)

    if child_hwnd == 0:
        return 0
    return _fmpw(child_hwnd, child_pid)


def _find_all_windows_by_pid(pid):
    '''

    Находит все окна по заданному PID
    :return: list of handle
    '''

    def EnumWindows_callback(hwnd, extra):                      # Callback на перебор всех окон. Вызывается для каждого окна.
        (_, processId) = GetWindowThreadProcessId(hwnd)  # По указателяю на окно получаем (threadId, processId)
        if processId == extra['pid']:
            extra['hwnds'].append(int(hwnd))

    for proc in psutil.process_iter():
        try:
            if proc.pid == pid:
                break
        except psutil.NoSuchProcess:
            pass
    else:
        raise FindFailed('pikuli.HWNDElement: can not find process with PID={}'.format(pid))

    extra = {'pid': pid, 'hwnds': []}

    EnumWindows(EnumWindows_callback, extra)

    return extra['hwnds']


def _find_window_by_process_name_and_title(proc_name, in_title):
    ''' По имени exe-файла и текстут в заголовке (in_title -- список строк, искомых в заголовке) ищет окно. Это
    может быть как обычное окно, так и любой другой windows-контрол. '''

    def EnumWindows_callback(hwnd, extra):                      # Callback на перебор всех окон. Вызывается для каждого окна.
        (_, processId) = GetWindowThreadProcessId(hwnd)  # По указателяю на окно получаем (threadId, processId)
        if processId == extra['pid']:
            text = GetWindowText(hwnd)
            for elem in extra['in_title']:
                if elem not in text:
                    return
            if 'hwnd' not in extra:
                extra['hwnd'] = int(hwnd)
            else:
                extra['hwnd'] = -1

    extra = {'in_title': in_title}
    for proc in psutil.process_iter():
        try:
            if proc.name() == proc_name:
                extra.update({'pid': proc.pid})
                break
        except psutil.NoSuchProcess:
            pass
    if extra is None:
        raise FindFailed('pikuli.HWNDElement: can not find process of \'%s\'' % str(proc_name))

    EnumWindows(EnumWindows_callback, extra)
    if 'hwnd' not in extra:
        raise FindFailed('pikuli.HWNDElement: can not find the window with %s in title of the process \'%s\' (%s).' % (str(in_title), str(proc_name), str(extra['pid'])))
    if extra['hwnd'] == -1:
        raise FindFailed('pikuli.HWNDElement: more then one window with %s in title of the process \'%s\' (%s) was found.' % (str(in_title), str(proc_name), str(extra['pid'])))

    return (extra['pid'], extra['hwnd'])


class HWNDElement(object):
    '''
    Доступные поля:
        proc_name      --  имя процесса (exe-файла), которому принадлежит окно
        pid            --  PID процесса, которому принадлежит окно
        hwnd           --  win32 указатель на искомое окно
        hwnd_main_win  --  win32 указатель главное окно процесса (самое родительское для искомого)
        title          --  заголовок искомого окна (для кнопок/чек-боксов/т.п. -- это их надписи)
    '''

    def __init__(self, *args, **kwargs):  # proc_name=None, in_title=None, parent=None, hwnd=None):
        '''
        Вариант №1 (новый экземпляр класса для главного окна):
            args[0]: proc_name  --  имя процесса, которое будет использоватья при поиске окна среди всех сущетсвующих окон
            args[1]: in_title   --  список строк, которые должны встречаться в заголовке окна.
            kwargs:
                     title_regexp  --  использовать ли регулярные выражения (True|False)

        Вариант №2 (экземпляр класса для какого-либо элемента главного окна):
            args[0]: hwnd       --  hwnd этого элемента окна.

        Вариант №3 (экземпляр класса для какого-либо элемента главного окна):
            args[0]: uia_element --  UIA елемент (класс UIAElement).

        Вариант №4:
            нет аргуметов       --  пустой экземпляр класса. Вызов его методов будет приводить к исключениям с понятными текстовыми сообщениями.
        '''

        self._id  = kwargs.get('id', None)  # Идентификатор для использования в коде.
        self._reg = None

        if len(args) == 2 and isinstance(args[0], types.StringType) and (isinstance(args[1], types.StringType) or isinstance(args[1], types.ListType)):
            self.proc_name = args[0]

            if not isinstance(args[1], types.ListType):
                self.main_wnd_in_title = [args[1]]
            else:
                self.main_wnd_in_title = args[1]

            if kwargs.get('title_regexp', False):
                raise Exception('TODO: title_regexp is unsupported yet!')

            (self.pid, self.hwnd) = _find_window_by_process_name_and_title(self.proc_name, self.main_wnd_in_title)
            self.hwnd_main_win   = _find_main_parent_window(self.hwnd)

        elif len(args) == 1 and (isinstance(args[0], int)):
            self.hwnd          = args[0]
            self.hwnd_main_win = _find_main_parent_window(self.hwnd)
            (_, self.pid)      = GetWindowThreadProcessId(self.hwnd)

            self.proc_name = None
            for proc in psutil.process_iter():
                try:
                    if self.pid == proc.pid:
                        self.proc_name = proc.name()
                        break
                except psutil.NoSuchProcess:
                    pass
            if self.proc_name is None:
                raise FindFailed('pikuli.HWNDElement: can not find name of process with PID = %s' % str(self.pid))

            '''# Проверим, что дочерний элемент:
            def EnumChildWindows_callback(hwnd, extra):
                if extra['hwnd'] == hwnd:
                    extra['res'] = True

            extra = {'hwnd': hwnd, 'res': False}
            EnumChildWindows(self.hwnd_main_win, EnumChildWindows_callback, extra)
            if not extra['res']:
                raise Exception('pikuli.HWNDElement: constructor error: hwnd = %s is not child for main window %s' % (str(hwnd), str(self.hwnd_main_win)))'''

        elif len(args) == 1 and isinstance(args[0], pikuli.uia.UIAElement):
            if args[0].hwnd is None or args[0].hwnd == 0:
                raise Exception('pikuli.HWNDElement: constructor error: args[0].hwnd is None or args[0].hwnd == 0:; args = %s' % str(args))
            self.hwnd          = args[0].hwnd
            self.hwnd_main_win = None
            self.pid           = args[0].pid
            self.proc_name     = args[0].proc_name

        elif len(args) == 0:
            self.hwnd_main_win = 0
            self.hwnd          = 0
            self.proc_name     = None

        else:
            raise Exception('pikuli.HWNDElement: constructor error; args = %s' % str(args))

        if not self.is_empty():
            self.class_name = GetClassName(self.hwnd)

    def get_id(self):
        return self._id

    def set_id(self, id):
        self._id = id

    def title(self):
        return GetWindowText(self.hwnd)


    '''def _hwnd2reg(self, hwnd, title=None):
        # полчение размеров клменскй области окна
        (_, _, wc, hc) = GetClientRect(hwnd)
        # получение координат левого верхнего угла клиенской области осносительно угла экрана
        (xc, yc) = ClientToScreen(hwnd, (0, 0) )
        reg = geom.Region(xc, yc, wc, hc)
        if hwnd == self.hwnd:
            reg.winctrl = self
        else:
            reg.winctrl = HWNDElement(hwnd)
        return reg'''


    def is_empty(self):
        return (self.proc_name is None)


    def find_all(self, win_class, title, process_name=False, title_regexp=False, max_depth_level=None, depth_level=None):
        return self.find(win_class, title, process_name=process_name, title_regexp=title_regexp, find_all=True, max_depth_level=max_depth_level, depth_level=depth_level)


    def find(self, win_class, title, process_name=False, title_regexp=False, find_all=False, max_depth_level=None, depth_level=None):  #, timeout=None):
        '''
        Поиск дочернего окна-объекта любого уровня вложенности. Под окном пнимается любой WinForms-элемент любого класса.
            win_class        --  Искомое окно должно обладать таким WinForms-классом.
            title            --  Искомое окно должно иметь такой заголвоок (текст); Варианты:
                                   1. title_regexp == False: Строка или список строк. Возвращается контрол с первым точным совпадением.
                                   2. title_regexp == True:  Регулярное выражение или их список. Возвращается контрол с первым regexp-совпадением.
            title_regexp     --  В title передается регулярное выржение для поиска.
            find_all         --  Если True, то возвращается список _всех_ найденных окон. Если False, то возвращается только одно значение или происходит Exception, если найдено несколько элементов.
            max_depth_level  --  максимальная глубина вложенности дочерних объектов. Нумерация от 1. None -- бесконечность. Взаимоисключающий с depth_level.
            depth_level      --  Взаимоисключающий с max_depth_level.
            timeout          --  Определяет время, в течение которого будет повторяься неудавшийся поиск. Дейстует только при find_all=False (при find_all=True поиск будет однократный).
                                 Возможные значения:
                                    timeout = 0     --  однократная проверка
                                    timeout = None  --  использование дефолтного значения
                                    timeout = <число секунд>

            Если title -- это re.compile, то аргумент title_regexp игнорируется.

        Возвращает:
            объект типа Region.
        '''

        if self.is_empty():
            raise Exception('pikuli.HWNDElement.find: this is an empty class. Initialise it first.')
        if max_depth_level is not None and depth_level is not None:
            raise Exception('pikuli.HWNDElement.find: max_depth_level is not None and depth_level is not None')

        if isinstance(title, list):
            for t in title:
                if not isinstance(t, str):
                    raise Exception('pikuli.HWNDElement.find: wrong title = \'%s\' (win_class = \'%s\')' % (str(title), str(win_class)))
        else:
            title = [title]

        check_all_regexp = [isinstance(t, re._pattern_type) or hasattr(t, 'match') for t in title]
        check_all_str    = [isinstance(t, str) for t in title]
        if False in check_all_regexp and True in check_all_regexp or \
           False in check_all_str and True in check_all_str:
            raise Exception('pikuli.HWNDElement.find: wrong title = \'%s\' (win_class = \'%s\') #1' % (str(title), str(win_class)))

        if True in check_all_regexp:
            # TODO: смонительгной правильности проверка выше.
            title_regexp = True
            extra = {'hwnds': [], 'in_title': title}
        elif True in check_all_str:
            if title_regexp:
                extra = {'hwnds': [], 'in_title': [re.compile(t) for t in title]}
            else:
                extra = {'hwnds': [], 'in_title': title}
        else:
            raise Exception('pikuli.HWNDElement.find: wrong title = \'%s\' (win_class = \'%s\') #2' % (str(title), str(win_class)))

        def EnumChildWindows_callback(hwnd, extra):
            if hwnd == 0:
                return
            for t in extra['in_title']:
                if ( (not title_regexp and t == GetWindowText(hwnd)) or (title_regexp and t.match(GetWindowText(hwnd))) )  and \
                   win_class.lower() in GetClassName(hwnd).lower():  # .split('.'):
                    if max_depth_level is None and depth_level is None:
                        extra['hwnds'] += [hwnd]
                    elif max_depth_level is not None:
                        _hwnd = hwnd  # Должна скопироваться не ссылка, а значание.
                        for l in range(max_depth_level):
                            _hwnd = GetParent(_hwnd)
                            if _hwnd == self.hwnd:
                                extra['hwnds'] += [hwnd]
                                break
                    else:
                        _hwnd = hwnd  # Должна скопироваться не ссылка, а значание.
                        for l in range(depth_level):
                            _hwnd = GetParent(_hwnd)
                        if _hwnd == self.hwnd:
                            extra['hwnds'] += [hwnd]
                    break
        EnumChildWindows(self.hwnd, EnumChildWindows_callback, extra)

        if len(extra['hwnds']) == 0:
            raise FindFailed('pikuli.HWNDElement.find: win_class = \'%s\' and title = \'%s\' was not found.' % (str(win_class), str(title)))

        if find_all:
            return [HWNDElement(h) for h in extra['hwnds'] if _is_visible(h)]

        else:
            if len(extra['hwnds']) != 1:
                try:
                    str_hwnds = map(hex, extra['hwnds'])
                except Exception:
                    str_hwnds = str(extra['hwnds'])
                raise FindFailed('pikuli.HWNDElement.find: more than one elemnt was found with win_class = \'%s\' and title = \'%s\': extra[\'hwnds\'] = %s' % (str(win_class), str(title), str_hwnds))

            if _is_visible(self.hwnd):
                return HWNDElement(extra['hwnds'][0])
            else:
                raise FindFailed('pikuli.HWNDElement.find: window %s with win_class = \'%s\' and title = \'%s\' has visible = False.' % (hex(extra['hwnds'][0]), str(win_class), str(title)))


    def reg(self, force_new_reg=False):
        ''' Возвращает Region для self-элемента HWNDElement. '''
        if self.is_empty():
            raise Exception('HWNDElement: this is an empty class. Initialise it first.')

        if force_new_reg or self._reg is None:
            # полчение размеров клменскй области окна
            (_, _, wc, hc) = GetClientRect(self.hwnd)
            # получение координат левого верхнего угла клиенской области осносительно угла экрана
            (xc, yc) = ClientToScreen(self.hwnd, (0, 0) )
            self._reg = Region(xc, yc, wc, hc, winctrl=self, title=self.title())

        return self._reg

    def bring_to_front(self):
        if self.is_empty():
            raise Exception(
                'HWNDElement: this is an empty class. Initialise it first.')
        try:
            SetForegroundWindow(self.hwnd)
            return True
        except Exception as ex:
            logger.error('HWNDElement: could not bring_to_front(): {}'.format(ex))
            return False

    def is_visible(self):
        ''' Определяет свойство visible искомого окна, а также проверяет наследвоание этого свойства от всех родительских окон. '''
        if self.is_empty():
            raise Exception('HWNDElement: this is an empty class. Initialise it first.')
        return _is_visible(self.hwnd)

    def wait_for_visible(self, timeout=5):
        if not wait_while_not(self.is_visible, timeout):
            raise Exception('pikuli.HWNDElement: wait_for_visible(...) of %s was failed' % str(self))

    def wait_for_invisible(self, timeout=5):
        if not wait_while(self.is_visible, timeout):
            raise Exception('pikuli.HWNDElement: wait_for_invisible(...) of %s was failed' % str(self))

    def _obj(self):
        comtypes.client.GetModule('oleacc.dll')  # Что-то там нагенерирует ...
        from comtypes.gen.Accessibility import IAccessible  # ... и теперь чать этого импортируем
        obj = comtypes.POINTER(IAccessible)()
        oledll.oleacc.AccessibleObjectFromWindow(self.hwnd, OBJID_CLIENT, byref(obj._iid_), byref(obj))
        return obj

    def is_button_checked(self):
        '''
        Возвращает True, если кнопка нажата, чек-бокс выбран. В противном случае возвращает False.
        Умеет работать с класическим GDI-контролом и WindowsForms.

        Полезные ссылки по теме WindowsForm:
            https://msdn.microsoft.com/en-us/library/windows/desktop/dd318466(v=vs.85).aspx
            https://github.com/phuslu/pyMSAA/blob/27250185fb27488ea9a914249b362d3a8b849d0e/comtypes/test/test_QueryService.py
            http://stackoverflow.com/questions/29392625/check-if-a-winform-checkbox-is-checked-through-winapi-only
            http://stackoverflow.com/questions/34008389/using-accessibleobjectfromwindow-in-python-on-microsoft-word-instance
            http://stackoverflow.com/questions/33901597/getting-last-opened-ms-word-document-object
        '''
        if self.is_empty():
            raise Exception('pikuli.HWNDElement: is_button_checked: This is an empty class. Initialise it first.')
        if 'button' not in self.class_name.lower():
            raise Exception('pikuli.HWNDElement: is_button_checked: hwnd = %s with ClassName = \'%s\' seems not to be a \'button\'' % (hex(self.hwnd), str(self.class_name)))

        if 'HWNDElements' in self.class_name.lower():
            state = self._obj().accState()
            return (state & CHECKED != 0)
        else:
            return bool(SendMessage(self.hwnd, BM_GETCHECK, 0, 0))

    def wait_for_button_checked(self, timeout=5):
        if not wait_while_not(self.is_button_checked, timeout):
            raise Exception('pikuli.HWNDElement: wait_for_button_checked(...) of %s was failed' % str(self))

    def wait_for_button_unchecked(self, timeout=5):
        if not wait_while(self.is_button_checked, timeout):
            raise Exception('pikuli.HWNDElement: wait_for_button_unchecked(...) of %s was failed' % str(self))


    def is_button_marked(self):
        '''
        В первую очередь, речь идет о кнопке Applay.
        '''
        if self.is_empty():
            raise Exception('pikuli.HWNDElement: is_button_marked: This is an empty class. Initialise it first.')
        if 'button' not in self.class_name.lower():
            raise Exception('pikuli.HWNDElement: is_button_marked: hwnd = %s with ClassName = \'%s\' seems not to be a \'button\'' % (hex(self.hwnd), str(self.class_name)))

        if 'HWNDElements' in self.class_name.lower():
            state = self._obj().accState()
            return (state & BUTTON_NOT_MARKED == 0)
        else:
            raise Exception('pikuli.HWNDElement: is_button_marked: Non-HWNDElements control is unsupported.')

    def wait_for_button_marked(self, timeout=5):
        if not wait_while_not(self.is_button_marked, timeout):
            raise Exception('pikuli.HWNDElement: wait_for_button_marked(...) of %s was failed' % str(self))

    def wait_for_button_unmarked(self, timeout=5):
        if not wait_while(self.is_button_marked, timeout):
            raise Exception('pikuli.HWNDElement: wait_for_button_unmarked(...) of %s was failed' % str(self))


    def get_editbox_text(self):
        ''' Вернет текст поля ввода '''
        if self.is_empty():
            raise Exception('pikuli.HWNDElement: get_editbox_text: This is an empty class. Initialise it first.')
        if 'edit' not in self.class_name.lower():
            raise Exception('pikuli.HWNDElement: get_editbox_text: hwnd = %s with ClassName = \'%s\' seems not to be a \'edit\'' % (hex(self.hwnd), str(self.class_name)))

        if 'HWNDElements' in self.class_name.lower():
            return str(self._obj().accValue())
        else:
            raise Exception('TODO')


    def get_combobox_text(self):
        ''' Вернет текст поля combobox '''
        if self.is_empty():
            raise Exception('pikuli.HWNDElement: get_combobox_text: This is an empty class. Initialise it first.')
        if 'combobox' not in self.class_name.lower():
            raise Exception('pikuli.HWNDElement: get_combobox_text: hwnd = %s with ClassName = \'%s\' seems not to be a \'edit\'' % (hex(self.hwnd), str(self.class_name)))

        if 'HWNDElements' in self.class_name.lower():
            return str(self._obj().accValue())
        else:
            raise NotImplementedError


    def get_parent(self):
        ''' Вернет HWNDElement для родительского окна (в широком виндовом смысле "окна"). '''
        return HWNDElement(GetParent(self.hwnd))




"""
import pywinauto
win32defines = pywinauto.win32defines

'''
-= Tree View: =-
    pywinauto.controls.common_controls.TreeViewWrapper (https://github.com/pywinauto/pywinauto)
    "About Tree-View Controls" (https://msdn.microsoft.com/en-us/en-en/library/windows/desktop/bb760017(v=vs.85).aspx)
    "Using Tree-View Controls" (https://msdn.microsoft.com/en-us/en-en/library/windows/desktop/bb773409(v=vs.85).aspx)
'''

def _treeview_element__reg(self):
    rect = self.Rectangle()
    return geom.Region(rect.left, rect.top, rect.width, rect.height)
setattr(pywinauto.controls.common_controls._treeview_element, 'reg', _treeview_element__reg)
"""
