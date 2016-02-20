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

import Region
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


# # Словарь "системых" title'ов. Если title не строка, а число отсюда, то title интерпретируется не просто как заголвок окна или текст лейбла, а как указание на какой-то объект.
# SYS_TITLES = {'main_window': 0}


def _hwnd2wf(hwnd):
    return WindowsForm(hwnd)


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
                if long(ppid) != long(child_pid):
                    return child_hwnd
        return _fmpw(parent_hwnd, child_pid)
    return _fmpw(child_hwnd, child_pid)



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
                extra['hwnd'] = long(hwnd)
            else:
                extra['hwnd'] = -1

    extra = {'in_title': in_title}
    for proc in psutil.process_iter():
        if proc.name() == proc_name:
            extra.update({'pid': proc.pid})
            break
    if extra is None:
        raise Exception('pikuli: winforms: can not find process of \'%s\'' % str(proc_name))

    EnumWindows(EnumWindows_callback, extra)
    if 'hwnd' not in extra:
        raise Exception('pikuli: winforms: can not find the window with %s in title of the process \'%s\' (%s).' % (str(in_title), str(proc_name), str(extra['pid'])))
    if extra['hwnd'] == -1:
        raise Exception('pikuli: winforms: more then oine window with %s in title of the process \'%s\' (%s) was found.' % (str(in_title), str(proc_name), str(extra['pid'])))

    return (extra['pid'], extra['hwnd'])



class WindowsForm(object):
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

        Вариант №3:
            нет аргуметов       --  пустой экземпляр класса. Вызов его методов будет приводить к исключениям с понятными текстовыми сообщениями.
        '''

        self._id = kwargs.get('id', None)  # Идентификатор для использования в коде.

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

        elif len(args) == 1 and (isinstance(args[0], types.IntType) or isinstance(args[0], types.LongType)):
            self.hwnd          = long(args[0])
            self.hwnd_main_win = _find_main_parent_window(self.hwnd)
            (_, self.pid)      = GetWindowThreadProcessId(self.hwnd)

            self.proc_name = None
            for proc in psutil.process_iter():
                if self.pid == proc.pid:
                    self.proc_name = proc.name()
                    break
            if self.proc_name is None:
                raise Exception('pikuli: winforms: can not find name of process with PID = %s' % str(self.pid))

            '''# Проверим, что дочерний элемент:
            def EnumChildWindows_callback(hwnd, extra):
                if extra['hwnd'] == hwnd:
                    extra['res'] = True

            extra = {'hwnd': hwnd, 'res': False}
            EnumChildWindows(self.hwnd_main_win, EnumChildWindows_callback, extra)
            if not extra['res']:
                raise Exception('pikuli: winforms: constructor error: hwnd = %s is not child for main window %s' % (str(hwnd), str(self.hwnd_main_win)))'''

        elif len(args) == 0:
            self.hwnd_main_win = 0
            self.hwnd          = 0
            self.proc_name     = None

        else:
            raise Exception('pikuli: winforms: constructor error; args = %s' % str(args))

        if not self.is_empty():
            self.title = GetWindowText(self.hwnd)
            self.class_name = GetClassName(self.hwnd)

    def get_id(self):
        return self._id

    def set_id(self, id):
        self._id = id


    '''def _hwnd2reg(self, hwnd, title=None):
        # полчение размеров клменскй области окна
        (_, _, wc, hc) = GetClientRect(hwnd)
        # получение координат левого верхнего угла клиенской области осносительно угла экрана
        (xc, yc) = ClientToScreen(hwnd, (0, 0) )
        reg = Region.Region(xc, yc, wc, hc)
        if hwnd == self.hwnd:
            reg.winctrl = self
        else:
            reg.winctrl = WindowsForm(hwnd)
        return reg'''


    def is_empty(self):
        return (self.proc_name is None)


    def find(self, win_class, title, process_name=False, title_regexp=False, return_list=False):
        '''
        Поиск дочернего окна-объекта любого уровня вложенности. Под окном пнимается любой WinForms-элемент любого класса.
            win_class     --  Искомое окно должно обладать таким WinForms-классом.
            title         --  Искомое окно должно иметь такой заголвоок (текст); в точности такое или это регулярное выражение, в зависимости от флага title_regexp.
            title_regexp  --  В title передается регулярное выржение для поиска.
            return_list   --  Если True, то возвращается список найденных окон. Если False, то возвращается только одно значение или происходит Exception, если найдено несколько элементов.
        Возвращает объект типа Region.
        '''

        if self.is_empty():
            raise Exception('WindowsForm: this is an empty class. Initialise it first.')

        if isinstance(title, str):
            title = [title]
        elif isinstance(title, list):
            for t in title:
                if not isinstance(t, str):
                    raise Exception('pikuli: winforms: find: wrond title = \'%s\' (win_class = \'%s\')' % (str(title), str(win_class)))
        else:
            raise Exception('pikuli: winforms: find: wrond title = \'%s\' (win_class = \'%s\')' % (str(title), str(win_class)))

        if title_regexp:
            extra = {'hwnds': [], 'in_title': [re.compile(t) for t in title]}
        else:
            extra = {'hwnds': [], 'in_title': title}

        def EnumChildWindows_callback(hwnd, extra):
            if hwnd == 0:
                return
            for t in extra['in_title']:
                if ( (not title_regexp and t == GetWindowText(hwnd)) or (title_regexp and t.match(GetWindowText(hwnd))) )  and  win_class.lower() in GetClassName(hwnd).lower().split('.'):
                        extra['hwnds'] += [hwnd]
        EnumChildWindows(self.hwnd_main_win, EnumChildWindows_callback, extra)

        if len(extra['hwnds']) == 0:
            raise FindFailed('pikuli: winforms: find: not win_class = \'%s\' and title = \'%s\' was found.' % (str(win_class), str(title)))

        if return_list:
            return [WindowsForm(h) for h in extra['hwnds'] if _is_visible(h)]

        else:
            if len(extra['hwnds']) != 1:
                raise Exception('pikuli: winforms: find: more than one elemnt was found with win_class = \'%s\' and title = \'%s\': extra[\'hwnds\'] = %s' %
                                (str(win_class), str(title), str(extra['hwnds'])))

            if _is_visible(self.hwnd_main_win):
                return WindowsForm(extra['hwnds'][0])
            else:
                raise FindFailed('pikuli: winforms: find: window %s with win_class = \'%s\' and title = \'%s\' has visible = False.' % (hex(extra['hwnds'][0]), str(win_class), str(title)))


    def reg(self):
        ''' Возвращает Region для self-элемента WindowsForm. '''
        if self.is_empty():
            raise Exception('WindowsForm: this is an empty class. Initialise it first.')

        # полчение размеров клменскй области окна
        (_, _, wc, hc) = GetClientRect(self.hwnd)
        # получение координат левого верхнего угла клиенской области осносительно угла экрана
        (xc, yc) = ClientToScreen(self.hwnd, (0, 0) )
        reg = Region.Region(xc, yc, wc, hc)
        reg._winctrl = self
        reg._title = self.title

        return reg

    def bring_to_front(self):
        if self.is_empty():
            raise Exception('WindowsForm: this is an empty class. Initialise it first.')
        try:
            SetForegroundWindow(self.hwnd)
            return True
        except Exception as ex:
            p2c('bring_to_front: %s' % str(ex))
            return False

    def is_visible(self):
        ''' Определяет свойство visible искомого окна, а также проверяет наследвоание этого свойства от всех родительских окон. '''
        if self.is_empty():
            raise Exception('WindowsForm: this is an empty class. Initialise it first.')
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
        if self.is_empty():
            raise Exception('WindowsForm: this is an empty class. Initialise it first.')

        if 'button' not in self.class_name.lower():
            raise Exception('pikuli: winforms: is_button_checked: hwnd = %s with ClassName = \'%s\' seems not to be a \'button\'' % (hex(self.hwnd), str(self.class_name)))

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


    def get_parent(self):
        ''' Вернет WindowsForm для родительского окна (в широком виндовом смысле "окна"). '''
        return WindowsForm(GetParent(self.hwnd))
