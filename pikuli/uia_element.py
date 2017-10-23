# -*- coding: utf-8 -*-

import psutil
from inspect import currentframe, getframeinfo, isclass
import time
import datetime
import traceback
import sys
import re
import logging
import json

import _ctypes
import win32gui

import UIA
import Region
from _functions import (wait_while,
                        wait_while_not, Key, KeyModifier,
                        type_text, verify_timeout_argument,
                        set_text_to_clipboard, get_text_from_clipboard)
from _exceptions import FindFailed, FailExit
import hwnd_element
from enum import Enum
from oleacc_h import (STATE_SYSTEM, ROLE_SYSTEM, ROLE_SYSTEM_rev)

# "A lot of HRESULT codes…" (https://blogs.msdn.microsoft.com/eldar/2007/04/03/a-lot-of-hresult-codes/)
COR_E_TIMEOUT = -2146233083  # -2146233083 =<математически>= -0x80131505;   0x80131505 =<в разрядной сетке>= (-2146233083 & 0xFFFFFFFF)
COR_E_SUBSCRIBERS_FAILED = -2147220991  # -2147220991 =<математически>= -0x80040201;
NAMES_of_COR_E = {
    COR_E_TIMEOUT: 'COR_E_TIMEOUT',
    COR_E_SUBSCRIBERS_FAILED: 'COR_E_SUBSCRIBERS_FAILED'
}


NEXT_SEARCH_ITER_DELAY = 2  # Задержка между итерациями поиска, пока ещё не вышел timeout
DEFAULT_FIND_TIMEOUT   = 11
CONTROL_CHECK_TIMEOUT = 20
DYNAMIC_FIND_TIMEOUT = None

CONSOLE_ERASE_LINE_SEQUENCE = '\033[F' + '\033[2K'

logger = logging.getLogger('axxon.pikuli')

'''
TODO:

    --- def check(self, method='click'):
        def click(self, method='click')
        Потенциально в качестве значения method могут быть click (подвести курсов мыши и кликнуть) или invoke (через UIA).

    --- обработка доступности LegacyIAccessiblePattern в основнмо классе UIAElement
'''

"""
'''
    Если в функции поиска ниже явно не передатся таймаут, то будет использоваться глобальная для модуля
переменная _default_timeout. Её _можно_ менять извне с помощью функций uia_set_default_timeout() и
uia_set_initial_default_timeout(). Это нужно для организации цеочки поиска с помощью db_class.
'''
if '_default_timeout' not in globals():
    _default_timeout = DEFAULT_FIND_TIMEOUT

def uia_set_default_timeout(timeout):
    global _default_timeout
    logger.debug('uia_set_default_timeout(): _default_timeout  %f -> %f' % (_default_timeout, timeout))
    _default_timeout = float(timeout)

def uia_set_initial_default_timeout():
    global _default_timeout
    logger.debug('uia_set_initial_default_timeout(): _default_timeout  %f -> %f' % (_default_timeout, DEFAULT_FIND_TIMEOUT))
    _default_timeout = DEFAULT_FIND_TIMEOUT
"""

def _None_of_str(arg):
    if arg is None:
        return None
    else:
        return str(arg)


class DriverException(Exception):
    pass


class Method(object):
    '''
    Wrapper class for UIA pattern method
    (code from https://github.com/xcgspring/AXUI)
    '''
    def __init__(self, function_object, name, args_expected=None):
        if args_expected is None:
            args_expected = []

        self.function_object = function_object
        self.name = name
        self.args = []
        self.outs = []
        for arg in args_expected:
            arg_direction = arg[0]
            arg_type = arg[1]
            arg_name = arg[2]
            if arg_direction == "in":
                self.args.append([arg_type, arg_name])
            elif arg_direction == "out":
                self.outs.append([arg_type, arg_name])
            else:
                # skip unsupported arg_direction
                raise DriverException("Unsupported arg_direction: %s" % arg_direction)

    def __repr__(self):
        docstring = "Name:\t"+self.name+"\n"
        argument_string = "+ Arguments: +\n"
        for argument in sorted(self.args):
            argument_type = argument[0]
            argument_name = argument[1]

            if argument_type == "POINTER(IUIAutomationElement)":
                argument_type = "UIAElement"
            elif argument_type in UIA.UIA_enums:
                argument_type = UIA.UIA_enums[argument_type]

            argument_string += "  Name:\t"+argument_name+"\n"
            argument_string += "  Type:\t"+repr(argument_type)+"\n\n"

        return_string = "+ Returns: +\n"
        for out in sorted(self.outs):
            return_name = out[1]
            return_type = out[0]
            return_string += "  Name:\t"+return_name+"\n"
            return_string += "  Type:\t"+return_type+"\n\n"

        docstring += argument_string
        docstring += return_string

        return docstring

    def __call__(self, *in_args):
        '''
        For output value, use original value
        For input arguments:
            1. If required argument is an enum, check if input argument fit requirement
            2. If required argument is "POINTER(IUIAutomationElement)", we accept UIAElement object,
               get required pointer object from UIAElement, and send it to function
            3. Other, no change
        '''
        args = list(in_args)
        if len(self.args) != len(args):
            # LOGGER.warn("Input arguments number not match expected")
            return None
        for index, expected_arg in enumerate(self.args):
            expected_arg_type = expected_arg[0]
            if expected_arg_type == "POINTER(IUIAutomationElement)":
                # get the UIAElment
                args[index] = args[index]._winuiaelem
            elif expected_arg_type in UIA.UIA_enums:
                # enum should be an int value, if argument is a string, should translate to int
                if args[index] in UIA.UIA_enums[expected_arg_type]:
                    args[index] = UIA.UIA_enums[expected_arg_type][args[index]]

                if args[index] not in UIA.UIA_enums[expected_arg_type].values():
                    # LOGGER.debug("Input argument not in expected value: %s" , args[index])
                    return None

        return self.function_object(*args)



def _unpack(flag, name, *args):
    return flag, name, args


class Pattern(object):
    '''
    Wrapper class for UIA pattern interface
    (code from https://github.com/xcgspring/AXUI)
    '''
    def __init__(self, winuiaelem, pattern_identifier):
        self._winuiaelem = winuiaelem
        self.pattern_object = UIA.get_pattern_by_id(winuiaelem, pattern_identifier)
        if self.pattern_object is None:
            raise DriverException("Cannot get pattern, stop init pattern object")
        self.methods = {}
        self.properties = {}
        interface_description = UIA.UIA_control_pattern_interfaces[pattern_identifier]
        for member_description in interface_description:
            flag, name, args = _unpack(*member_description)
            # do a check, see if member exist in pattern object
            # if not, skip this member
            try:
                getattr(self.pattern_object, name)
            except AttributeError:
                # LOGGER.debug("%s not exist in Pattern:%s", name, pattern_identifier)
                continue

            if flag == "method":
                self.methods[name] = args
            elif flag == "property":
                self.properties[name] = args
            else:
                raise DriverException("Unrecognised flag %s" % flag)

    def __str__(self):
        docstring = ""
        docstring += "Properties:\n"
        for property_ in self.properties.items():
            name = property_[0]
            argument = property_[1][0]
            value_type = argument[1]
            value = getattr(self.pattern_object, name)
            docstring += "#"*32+"\n"
            docstring += "  Name:\t"+name+"\n"
            docstring += "  Value Type:\t"+value_type+"\n"
            docstring += "  Value:\t"+repr(value)+"\n"

        docstring += "\nMethods:\n"
        for method_ in self.methods.items():
            name = method_[0]
            arguments = method_[1]
            docstring += "#"*32+"\n"
            docstring += "  Name:\t"+name+"\n"
            argument_string = "  Arguments:\n"
            return_string = "  Return:\n"
            for argument in arguments:
                argument_direction = argument[0]
                argument_type = argument[1]
                argument_name = argument[2]

                if argument_direction == "in":
                    if argument_type == "POINTER(IUIAutomationElement)":
                        argument_type = "UIAElement"
                    elif argument_type in UIA.UIA_enums:
                        argument_type = UIA.UIA_enums[argument_type]

                    argument_string += "    Name:\t"+argument_name+"\n"
                    argument_string += "    Type:\t"+repr(argument_type)+"\n\n"
                elif argument_direction == "out":
                    return_string += "    Name:\t"+argument_name+"\n"
                    return_string += "    Type:\t"+argument_type+"\n\n"

            docstring += argument_string
            docstring += return_string

        return docstring

    def __getattr__(self, name):
        member_object = getattr(self.pattern_object, name)
        if name in self.methods:
            return Method(member_object, name, self.methods[name])
        elif name in self.properties:
            return member_object
        else:
            raise AttributeError("Attribute not exist: %s" % name)




class UIAElement(object):
    '''
    Доступные поля:
        pid        --  PID процесса, которому принадлежит окно
        hwnd       --  win32 указатель на искомое окно
        name()     --  заголовок искомого окна (для кнопок/чек-боксов/т.п. -- это их надписи)
        proc_name  --  имя процесса (exe-файла), которому принадлежит окно
    '''

    def __init__(self, pointer2elem, derived_self=None, find_timeout=DEFAULT_FIND_TIMEOUT):  #, timeout=10):
        '''
        Аргументы:
            pointer2elem       --  Некий указатель на UI-элемент (см. ниже).
            derived_self       --  Если пришли сюда из конструктора дочернего класса, то здесь хранится self создаваемого объета (можно узнать тип дочернего класса)
            find_timeout       --  Значение по умолчанию, которове будет использоваться, если метод find() (и подобные) этого класса вызван без явного указания timeout.
                                   Если не передается конструктуру, то берется из переменной модуля DEFAULT_FIND_TIMEOUT.
                                   Будет наслодоваться ко всем объектам, которые возвращаются методами этого класса.
            #timeout            --  Если происходит какая-то ошибка, что пробуем повторить ошибочную процедуру, пока не превысим timeout. Пока ошибка может быть только в происке процесса по PID.

        Возможные значения аргумента pointer2elem:
            a) pointer2elem == hwnd искомого элемента GUI. В часности ноль -- это указатель корневой UIA-элемент ("рабочий стол").
            b) pointer2elem -- это уже интерфейс к искомому элементу GUI (указатель на обект типа IUIAutomationElement или экземпляр настоящего класса UIAElement)

        Возвращение методами этого класса объектов UI-элементов (реализовано в методе __create_instance_of_suitable_class):
             1. Если self._winuiaelem позволяет получить ControlType, ищется подходящий класс (дочерний для _uielement_Control) с сооветствующим занчением атрибута CONTROL_TYPE.
             2. Если self._winuiaelem = 'Custom', то запрашивается LegacyIAccessible.Role и ищется класс с сответствующим значением LEGACYACC_ROLE.
             3. Если по какой-то причние пункты 1 и 2 выше не позволили подобрать класс, то испульзуется родительский UIAElement.
             4. Если нашлось несколько подходящих классов, то генерируется исключение.
        '''
        self._reg = None
        self._find_timeout = verify_timeout_argument(find_timeout, err_msg='pikuli.UIAElement.__init__()')
        self._proc_name = None  # Кеш для proc_name

        if pointer2elem == 0:
            # Коренвой элемент.
            self._winuiaelem = UIA.IUIAutomation_object.GetRootElement()
            self._from_hwnd = True
            self.pid = None
            self.hwnd = 0

            self._has_proc_name = False  # Объект будет возвращать None при запросе proc_name

        else:
            if isinstance(pointer2elem, UIA.type_IUIAutomationElement):
                self._winuiaelem = pointer2elem
                self._from_hwnd = False
            elif isinstance(pointer2elem, UIAElement):
                self._winuiaelem = pointer2elem._winuiaelem
                self._from_hwnd = False
            elif isinstance(pointer2elem, int) or isinstance(pointer2elem, long):
                self._winuiaelem = UIA.IUIAutomation_object.ElementFromHandle(pointer2elem)
                self._from_hwnd = True
            else:
                raise Exception('pikuli.UIAElement: can not construct UIAElement')

            self.pid = self._winuiaelem.CurrentProcessId
            self.hwnd = self._winuiaelem.CurrentNativeWindowHandle

            self._has_proc_name = True  # Объект будет возвращать proc_name


    @property
    def proc_name(self):
        if self._has_proc_name and (self._proc_name is None):
            for proc in psutil.process_iter():
                try:
                    _processes = proc.as_dict(attrs=['pid', 'name'])
                    if proc.pid == self._winuiaelem.CurrentProcessId:
                        proc_name = proc.name()
                        break
                except psutil.NoSuchProcess:
                    pass
            if proc_name is None:
                raise Exception('pikuli.ui_element.UIAElement.__init__(): self.proc_name is None -- Cannot find process with self.pid = %s and self.hwnd = %s\n\trepr(self) = %s\n\tstr(self):%s\n\tprocesses:\n%s'
                                % (str(self.pid), str(self.hwnd), repr(self), str(self), str(_processes)))
        return proc_name

    def __getattr__(self, name):
        '''
        we also support direct use name to get object
        '''
        attr = self.get_property(name)
        if attr is not None:
            return attr
        attr = self.get_pattern(name)
        if attr is not None:
            return attr
        raise AttributeError("Attribute not exist: %s\n  self: %s\n%s" % (name, repr(self), str(self)))

    def _short_info(self):
        hwnd = getattr(self, 'NativeWindowHandle', '')
        if hwnd:
            try:
                hwnd = hex(int(hwnd)).upper().replace('X', 'x')
            except:
                pass
            hwnd = ', ' + str(hwnd)

        name = repr(self.Name)  #.encode('utf-8')
        if type(self).__name__ in CONTROLS_CLASSES:
            return u'<%s \'%s\',\'%s\'%s>' % (
                type(self).__name__,
                name,
                getattr(self, 'AutomationId', ''),
                hwnd)

        control_type_id = self.get_property('ControlType')
        legacy_role_id = getattr(self.get_pattern('LegacyIAccessiblePattern'), 'CurrentRole', None)  # LegacyIAccessiblePattern will be None in case of CustomControl.
        return u'<%s %s, %s,\'%s\',\'%s\',\'%s\',%s>' % (
            type(self).__name__,
            UIA.UIA_automation_control_type_identifiers_mapping_rev.get(control_type_id, control_type_id),
            ROLE_SYSTEM_rev.get(legacy_role_id, legacy_role_id),
            name,
            getattr(self, 'AutomationId', ''),
            getattr(self, 'LocalizedControlType', ''),
            hwnd)

    def _long_info(self):
        docstring = ""
        # generate UIA automation element properties
        docstring += "+ UIA automation element properties: +\n"
        for identifier in sorted(UIA.UIA_automation_element_property_identifers_mapping):
            value = self.get_property(identifier)
            if value is not None:
                docstring += "  %-24s:\t%s\n" % (identifier, repr(value))

        docstring += "\n"
        # generate UIA control pattern availability properties (from "Control Pattern Identifiers")
        docstring += "+ UIA control pattern availability properties: +\n"
        for identifier in sorted(UIA.UIA_control_pattern_availability_property_identifiers_mapping):
            value = self.get_property(identifier)
            if value is not None:
                docstring += "  %-35s:\t%s\n" % (identifier, repr(value))

        return docstring

    def __str__(self):
        return self._short_info()

    def __repr__(self):
        return self._short_info()

    def get_help_text(self):
        return json.loads(self.HelpText or {})

    def get_bounding_rectangle(self):
        return self.BoundingRectangle or {}

    def get_first_child(self):
        return self.FirstChild or None

    def get_details(self):
        return self._long_info()

    def get_property(self, name):
        if not hasattr(self, '_winuiaelem'):
            raise Exception('pikuli.UIAElement.find [INTERNAL]: self <class \'%s\'> not hasattr(self, \'_winuiaelem\')' % type(self).__name__)
        return UIA.get_property_by_id(self._winuiaelem, name)

    def get_pattern(self, name):
        if not hasattr(self, '_winuiaelem'):
            raise Exception('pikuli.UIAElement.find [INTERNAL]: self <class \'%s\'> not hasattr(self, \'_winuiaelem\')' % type(self).__name__)
        try:
            pattern = Pattern(self._winuiaelem, name)
        except DriverException:
            pattern = None
        return pattern

    def _test4readiness(self):
        ''' TODO: По идеи, надо сделать некую проврку, что класс создан правильно и готов к использованию.
        if self.is_empty():
            raise Exception('pikuli.UIAElement.find: this is an empty class. Initialise it first.')'''
        return True


    def __create_instance_of_suitable_class(self, winuielem):
        MAX_ERROR_TIMES  = 3
        EACH_ERROR_DELAY = 1
        _counter = 0

        while True:
            try:
                winuielem_ControlType = UIA.get_property_by_id(winuielem, 'ControlType')
                winuielem_CurrentRole = getattr(UIA.get_pattern_by_id(winuielem, 'LegacyIAccessiblePattern'), 'CurrentRole', None)  # LegacyIAccessiblePattern will be None in case of CustomControl.
                class_by_controltype  = class_by_legacy = None

                for class_ in CONTROLS_CLASSES:
                    # Очередной анализируемый класс имеет следующие поля:
                    class_control_type           = getattr(globals()[class_], 'CONTROL_TYPE', None)
                    class_legacy_accessible_role = getattr(globals()[class_], 'LEGACYACC_ROLE', None)

                    if class_control_type is None:
                        raise Exception('pikuli.UIAElement [INTERNAL]: CONTROL_TYPE is not setted for <class %s>. Processing controll \'%s\'' % (class_, UIAElement(winuielem).Name))

                    elif class_control_type != 'Custom' and winuielem_ControlType != UIA.UIA_automation_control_type_identifiers_mapping['Custom']:
                        class_control_type_id = UIA.UIA_automation_control_type_identifiers_mapping.get(class_control_type, None)  # Ищем тип class_control_type среди известных нам.
                        if class_control_type_id is None:
                            raise Exception('pikuli.UIAElement [INTERNAL]: CONTROL_TYPE = \'%s\' in <class %s> is unknown.Processing controll \'%s\'' % (class_control_type, class_, UIAElement(winuielem).Name))
                        if winuielem_ControlType == class_control_type_id:
                            if class_by_controltype is not None or class_by_legacy is not None:
                                raise Exception('pikuli.UIAElement [INTERNAL]: more than one class are suitable for UI-element \'%s\':' % UIAElement(winuielem).Name +
                                                '\n\tclass_by_controltype = \'%s\'\n\tclass_by_legacy = \'%s\'\n\tclass_ = \'%s\'' % (class_by_controltype, class_by_legacy, class_))
                            class_by_controltype = class_

                    elif class_control_type == 'Custom' and winuielem_ControlType == UIA.UIA_automation_control_type_identifiers_mapping['Custom']:
                        if class_legacy_accessible_role is None:
                            raise Exception('pikuli.UIAElement [INTERNAL]: CONTROL_TYPE = \'Custom\', but LEGACYACC_ROLE is not setted for <class %s>. Processing controll \'%s\'' % (class_, UIAElement(winuielem).Name))
                        else:
                            class_legacy_accessible_role_id = ROLE_SYSTEM.get(class_legacy_accessible_role, None)
                            if class_legacy_accessible_role_id is None:
                                raise Exception('pikuli.UIAElement [INTERNAL]: \'class_legacy_accessible_role_id\' is None for UIAElement Control \'%s\'.' % UIAElement(winuielem).Name)
                            if winuielem_CurrentRole == class_legacy_accessible_role_id:
                                if class_by_controltype is not None or class_by_legacy is not None:
                                    raise Exception('pikuli.UIAElement [INTERNAL]: more than one class are suitable for UI-element \'%s\':' % UIAElement(winuielem).Name +
                                                    '\n\tclass_by_controltype = \'%s\'\n\tclass_by_legacy = \'%s\'\n\tclass_ = \'%s\'' % (class_by_controltype, class_by_legacy, class_))
                                class_by_legacy = class_

                if class_by_controltype is not None:
                    return globals()[class_by_controltype](winuielem, find_timeout=self._find_timeout)
                elif class_by_legacy is not None:
                    return globals()[class_by_legacy](winuielem, find_timeout=self._find_timeout)
                else:
                    return UIAElement(winuielem, find_timeout=self._find_timeout)

                _counter += 1

            except _ctypes.COMError as ex:
                time.sleep(EACH_ERROR_DELAY)
                if _counter >= MAX_ERROR_TIMES:
                    raise Exception('pikuli.UIAElement.__create_instance_of_suitable_class: COMError too many times (max times %i with delay %i)' % (MAX_ERROR_TIMES, EACH_ERROR_DELAY))


    def set_find_timeout(self, timeout):
        if timeout is None:
            self._find_timeout = DEFAULT_FIND_TIMEOUT
        else:
            self._find_timeout = verify_timeout_argument(timeout, err_msg='pikuli.UIAElement.set_find_timeout()')

    def get_find_timeout(self):
        return self._find_timeout


    def find_all(self, **kwargs):
        kwargs['find_first_only'] = False
        kwargs['_find_all'] = True
        return self.find(**kwargs)

    def find_nested(self, *args, **kwargs):
        """
        Поис вложенных один в другой котролов. Иными словами, по цепочке делает несколько `find`'ов:
        :param *args: Это список словарей-критериев поиска. Очередной словарь -- очередная процедура
                      поиска `find`'ом относительно элменета, полученного как результат предыдущего поиска. Все
        :param **kwargs: Здесь применяются к притериям поиска на каждом шаге.
        """
        elem = self
        for crit in args:
            # So that we don't mutate the original args.
            params = crit.copy()
            params.update(**kwargs)
            elem = elem.find(**params)
            if elem is None:
                return None
        return elem

    def find_by_control(self, *names, **kwargs):
        """
        Поиск кложенных один в другой контролов пои их 'LocalizedControlType' при жестком условии
        на каждом шаге: {'exact_level': 1}.

        :param names: Список LocalizedControlType, которые будут искаться как вложенные один в
                      другой контролы (используется метод `find_nested`).
        :param kwargs: Передаются как kwargs в `find_nested`.
        """
        steps = [{'exact_level': 1, 'LocalizedControlType': n} for n in names]
        return self.find_nested(*steps, **kwargs)

    #def find(self, _criteria, find_first_only=True, max_descend_level=None, exact_level=None, exception_on_find_fail=None):
    #def find(self, AutomationId=True, ClassName=True, Name=True, ControlType=True, ProcessId=True,
    #         find_first_only=True, max_descend_level=None, exact_level=None, exception_on_find_fail=None):
    def find(self, **kwargs):
        '''
        Поиск дочернего окна-объекта любого уровня вложенности. Под окном пнимается любой WinForms-элемент любого класса.

        В **kwargs можно передавать следующие поля, использующиеся для сравнения с одноименноыми UIA-свойствами элементов интерфейса:
            AutomationId          --  Неки текстовый ID, который, видимо, может назанчаться при создании тестируемой программы.
            ClassName             --  Имя класса. К примеру, "WindowsForms10.Window.8.app.0.1e929c1_r9_ad1".
            Name                  --  Имя (title) искомого элемента UI.
            ControlType           --  Тип контрола. Строковое название из структуры UIA_automation_control_type_identifiers_mapping / списка UIA_automation_control_type_identifiers.
                                      (см. также "Control Type Identifiers", https://msdn.microsoft.com/en-us/library/windows/desktop/ee671198(v=vs.85).aspx)
            LocalizedControlType  --  Локализованное название контрола.
            ProcessId             --  Для UAI это число (PID). Дополним возможность указания строки -- имени исполняемого файла, по которому предварительно будем определять PID.

            AutomationId, ClassName, Name --  Строка или "скомпилированное" регулярное выржение (объект от re.compile()).

        Наличие нескольких критериев подразумевает логические AND между ними.

        При поиске [AutomationId, Name, ClassName] парметр может быть:
            1. Строкой. Элемент UI будет добавлять к списку найденных, если эта строка точно соответствует его атрибуту (с учетом регистра).
            2. Списком строк. Каждая из этих строка должна быть подстрокой в атрибуте искомого элемента UI (с учетом регистра).
            3. re.compile

        Также в **kwargs возможны следующие управляющие инструкции:
            find_first_only    --  Если False, то возвращается список _всех_ найденных окон (пустой, если ничего не найдено).
                                   Если True, то возвращается только одно значение первого найденного элемента (после первого обнаружения поиск останавливается!). Если ничего
                                   не найденно, то возвращает None или создает исключение (см. exception_on_find_fail).
            max_descend_level  --  Максимальная глубина вложенности дочерних объектов. Нумерация от 1. None -- бесконечность. Взаимоисключающий с exact_level параметр.
                                   Здесь рассматривается дерево из UI объектов всех возможных типов (TreeWalker, например, создает свое дерево, соответствующее condition'у поиска)
            exact_level        --  Искать элементы строго такой глубины. Взаимоисключающий с max_descend_level параметр.
                                    = 0 -- поиск среди соседних
                                    > 0 -- поиск среди дочерних выбранной глубины
                                    < 0 -- возвращает предка выбранной дальности
            exception_on_find_fail  --  По умолчанию None. Это означает, что переприсовится True при find_first_only = True, False при find_first_only = False.
            timeout            --  Если ищем только один эелемент (find_first_only=True) и ничего не нашлось, то будем повторять попытки в течение этого времени.
                                   Не оказывает влияния на поиск всех элементов (find_first_only=False). Возможные значения:
                                        timeout = 0     --  однократная проверка
                                        timeout = None  --  использование дефолтного значения (по умолчанию)
                                        timeout = <число секунд>

            _find_all  --  служебный (если True, то find() знает, что ее вызвали из find_all())

        Возвращает:
            объект типа Region.
        '''
        self._test4readiness()


        # Обработка воходных аргументов:
        find_first_only        = kwargs.pop('find_first_only', True)
        max_descend_level      = kwargs.pop('max_descend_level', None)
        exact_level            = kwargs.pop('exact_level', None)
        exception_on_find_fail = kwargs.pop('exception_on_find_fail', None)
        timeout = _timeout     = verify_timeout_argument(kwargs.pop('timeout', None), allow_None=True, err_msg='pikuli.UIAElement.__init__()')
        next_serach_iter_delya = kwargs.pop('next_serach_iter_delya', NEXT_SEARCH_ITER_DELAY)
        _find_all              = kwargs.pop('_find_all', False)

        # logger.debug('find: timeout = %s; self._find_timeout = %s' % (str(timeout), str(self._find_timeout)))
        if timeout is None:
            if DYNAMIC_FIND_TIMEOUT is not None:
                timeout = DYNAMIC_FIND_TIMEOUT
            else:
                timeout = self._find_timeout
        if exception_on_find_fail is None:
            exception_on_find_fail = find_first_only
        if _find_all:
            _func_name = 'pikuli.UIAElement.find_all'
        else:
            _func_name = 'pikuli.UIAElement.find'

        if max_descend_level is not None and exact_level is not None:
            raise Exception('%s: max_descend_level is not None and exact_level is not None' % _func_name)
        if max_descend_level is not None and max_descend_level < 1:
            raise Exception('%s: max_descend_level is not None and max_descend_level < 1' % _func_name)

        criteria = {}
        not_none_criteria = {}
        for key in ['AutomationId', 'ClassName', 'Name', 'LocalizedControlType']:
            val = kwargs.pop(key, None)
            if val is not None:
                not_none_criteria[key] = val
                if isinstance(val, re._pattern_type) or hasattr(val, 'match'):
                    pass
                elif isinstance(val, (list, tuple)):
                    val = map(str, val)
                else:
                    val = str(val)
            criteria[key] = val

        val = kwargs.pop('ControlType', None)
        if val is not None:
            not_none_criteria['ControlType'] = val
            if val not in UIA.UIA_automation_control_type_identifiers_mapping:
                raise Exception('%s: ControlType is not None (\'%s\'), but not from UIA.UIA_automation_control_type_identifiers_mapping' % (_func_name, val))
            val = UIA.UIA_automation_control_type_identifiers_mapping[val]
        criteria['ControlType'] = val

        val = kwargs.pop('ProcessId', None)
        if val is not None:
            if isinstance(val, str):
                not_none_criteria['ProcessId'] = val
                for proc in psutil.process_iter():
                    try:
                        if val == proc.name():
                            val = proc.pid
                            break
                    except psutil.NoSuchProcess:
                        pass
            if isinstance(val, str):
                logger.error('Pikuli Cannot find process by name')
                raise Exception('%s(): can not find process by its name: "%s"' % (_func_name, str(val)))
        criteria['ProcessId'] = val

        # Сделаем not_none_criteria и criteria, которые выводится на экран, крсивее:
        #   -- информативный вывод регулярных выражений
        def _criteria_pretty_print(cri):
            _cri = {}
            for (k, v) in cri.items():
                if hasattr(v, 'pattern'):
                    _cri[k] = v.pattern
                else:
                    _cri[k] = v
            return str(_cri)
        str__not_none_criteria = _criteria_pretty_print(not_none_criteria)
        str__criteria          = _criteria_pretty_print(criteria)

        if len(kwargs) != 0:
            raise Exception('%s: kwargs has unknown fields %s\n\tkwargs = %s' % (_func_name, kwargs.keys(), str(kwargs)))

        #  Начинаем поиск по очереди по всем критериям. Поиск элементов с помощью рекурсивного
        # вызова нашей функции. Будем искать через TreeWalker с условием CreateTrueCondition(), так
        # как простая функция поиска не позволяет (судя по документации) искать родителя:
        class FirstFoundEx(Exception):
            def __init__(self, winuiaelem):
                self.winuiaelem = winuiaelem
                super(Exception, self).__init__()


        def _is_winuiaelem_suitable(winuiaelem):
            if criteria['ProcessId'] is not None and criteria['ProcessId'] != winuiaelem.CurrentProcessId:
                return False

            if criteria['ControlType'] is not None and \
               criteria['ControlType'] != winuiaelem.GetCurrentPropertyValue(UIA.UIA_automation_element_property_identifers_mapping['ControlType']):
                return False

            for key in ['AutomationId', 'ClassName', 'Name', 'LocalizedControlType']:
                if criteria[key] is None:
                    continue
                try:
                    uielem_val = winuiaelem.GetCurrentPropertyValue(UIA.UIA_automation_element_property_identifers_mapping[key])
                except Exception as ex:
                    raise ex
                if isinstance(criteria[key], list):
                    for substr in criteria[key]:
                        if uielem_val is None or not (substr in uielem_val):
                            return False
                elif isinstance(criteria[key], str):
                    if not (uielem_val == criteria[key]):
                        return False
                elif isinstance(criteria[key], re._pattern_type) or hasattr(criteria[key], 'match'):  # re.complile
                    if not (criteria[key].match(uielem_val) is not None):
                        return False
                else:
                    raise Exception('%s: unsupported value \"%s\" of key \'%s\'' % (_func_name, str(criteria[key]), str(key)))

            return True


        def _search_with_method(start_winuiaelem, method_f):
            found_winuiaelem_arr_local = []
            next_winuiaelem = method_f(start_winuiaelem)
            while next_winuiaelem:
                if _is_winuiaelem_suitable(next_winuiaelem):
                    if find_first_only:
                        raise FirstFoundEx(next_winuiaelem)
                    found_winuiaelem_arr_local.append(next_winuiaelem)
                next_winuiaelem = method_f(next_winuiaelem)
            return found_winuiaelem_arr_local


        '''
        # Поиск по веткам элементов:
        def _descendants_range_level(walker, winuiaelem, level=0):
            found_winuiaelem_arr = []

            if max_descend_level is None or level < max_descend_level:  # max_descend_level > 0; level от вызова к вызову +1 (растет от 0).
                child_winuiaelem = walker.GetFirstChildElement(winuiaelem)
                while child_winuiaelem:
                    if _is_winuiaelem_suitable(child_winuiaelem):
                        if find_first_only:
                            raise FirstFoundEx(child_winuiaelem)
                        found_winuiaelem_arr += [child_winuiaelem]

                    if max_descend_level is None or level < max_descend_level - 1:
                        found_winuiaelem_arr += _descendants_range_level(walker, child_winuiaelem, level+1)

                    child_winuiaelem = walker.GetNextSiblingElement(child_winuiaelem)

            return found_winuiaelem_arr'''

        # Поиск по слоям вложенности:
        def _descendants_range_level(walker, winuiaelem):
            found_winuiaelem_arr   = []
            current_level_todo_arr = []
            next_level_todo_arr    = []
            level                  = 0

            def _add_to_next_level_todo(root_elem):
                if max_descend_level is None or level < max_descend_level:
                    elem   = walker.GetFirstChildElement(root_elem)
                    while elem:
                        next_level_todo_arr.append( elem )
                        elem = walker.GetNextSiblingElement(elem)

            def _goto_next_level():
                return (next_level_todo_arr, [], level+1)

            _add_to_next_level_todo(winuiaelem)
            (current_level_todo_arr, next_level_todo_arr, level) = _goto_next_level()

            while len(current_level_todo_arr) != 0:

                while len(current_level_todo_arr) != 0:
                    elem = current_level_todo_arr.pop(0)
                    if _is_winuiaelem_suitable(elem):
                        if find_first_only:
                            raise FirstFoundEx(elem)
                        found_winuiaelem_arr.append( elem )
                    _add_to_next_level_todo(elem)


                (current_level_todo_arr, next_level_todo_arr, level) = _goto_next_level()

            return found_winuiaelem_arr


        def _descendants_exact_level(walker, winuiaelem, level=0):
            if level < exact_level:  # exact_level > 0; level от вызова к вызову +1 (растет от 0).
                found_winuiaelem_arr = []
                child_winuiaelem = walker.GetFirstChildElement(winuiaelem)
                while child_winuiaelem:

                    found_winuiaelem_arr += _descendants_exact_level(walker, child_winuiaelem, level+1)
                    child_winuiaelem = walker.GetNextSiblingElement(child_winuiaelem)
                return found_winuiaelem_arr

            elif level == exact_level:
                if _is_winuiaelem_suitable(winuiaelem):
                    if find_first_only:
                        raise FirstFoundEx(winuiaelem)
                    return [winuiaelem]
                return []

            else:  # exact_level > 0 && level > exact_level
                raise Exception('%s: exact_level > 0 && level > exact_level\n\texact_level = %s\n\tlevel = %s' %
                                tuple(map(str, [_func_name, exact_level, level])))
        # - subroutines: end -
        txt_search_timeout        = 'searching with timeout = %s (call/class/module: %s/%s/%s) ...' % (str(timeout), str(_timeout), str(self._find_timeout), str(DEFAULT_FIND_TIMEOUT))
        txt_pikuli_search_pattern = '%s: by criteria %s %%s' % (_func_name, str__not_none_criteria)
        logger.debug(txt_pikuli_search_pattern % txt_search_timeout)

        walker = UIA.IUIAutomation_object.CreateTreeWalker(UIA.IUIAutomation_object.CreateTrueCondition())
        t0 = datetime.datetime.today()
        while True:
            try:
                # Исключение FirstFoundEx используется как goto.
                if exact_level is not None:
                    # Обработаем варианты поиска предков:
                    if exact_level < 0:
                        winuiaelem = self._winuiaelem
                        for level in range(-exact_level):
                            winuiaelem = walker.GetParentElement(winuiaelem)
                        if find_first_only:
                            # TODO: можом получить структуру winuiaelem, указывающую на ptr=0, если нет родителя заданного уровня. Надо обработать, но не знаю пока как.
                            raise FirstFoundEx(winuiaelem)
                        found_winuiaelem_arr = [winuiaelem]

                    # Обработаем варианты поиска братьев-сестер:
                    elif exact_level == 0:
                        found_winuiaelem_arr = _search_with_method(self._winuiaelem, walker.GetNextSiblingElement)
                        if find_first_only and len(found_winuiaelem_arr) != 0:
                            raise FirstFoundEx(found_winuiaelem_arr[0])
                        found_winuiaelem_arr += _search_with_method(self._winuiaelem, walker.GetPreviousSiblingElement)
                        if find_first_only:
                            if len(found_winuiaelem_arr) == 0:
                                raise FirstFoundEx(None)
                            raise FirstFoundEx(found_winuiaelem_arr[0])

                    # Обработаем вариант поиска потомков (descendants).
                    else:
                        # Поиск по веткам элементов:
                        found_winuiaelem_arr = _descendants_exact_level(walker, self._winuiaelem)
                        if find_first_only:
                            if len(found_winuiaelem_arr) == 0:
                                raise FirstFoundEx(None)
                            raise FirstFoundEx(found_winuiaelem_arr[0])

                else:
                    # Теперь обработаем вариант поиска потомков в диапазоне возможных вложенностей.
                    # Будем искать по слоям вложенности элементов, а не по веткам. Это немного сложнее сделать, но должно быть эффективнее.
                    found_winuiaelem_arr = _descendants_range_level(walker, self._winuiaelem)

                if find_first_only and len(found_winuiaelem_arr) == 0:
                    raise FirstFoundEx(None)

            except FirstFoundEx as ex:
                if ex.winuiaelem is None:
                    if (datetime.datetime.today()-t0).total_seconds() >= timeout:
                        if exception_on_find_fail:
                            raise FindFailed('%s: no one elements was found\n\tself     = %s\n\tkwargs   = %s\n\tcriteria = %s\n\ttimeout  = %s'
                                             % (_func_name, repr(self), str(kwargs), str__criteria, str(timeout)))
                        # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
                        logger.debug(txt_pikuli_search_pattern % 'has been found: None (%s)' % str(timeout))
                        return None
                    # t0 = datetime.datetime.today()
                    time.sleep(next_serach_iter_delya)
                else:
                    found_elem = self.__create_instance_of_suitable_class(ex.winuiaelem)
                    # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
                    logger.debug(txt_pikuli_search_pattern % ('has been found: %s (%s)' % (repr(found_elem), str(timeout))))
                    return found_elem

            except _ctypes.COMError as ex:
                if ex.args[0] == COR_E_TIMEOUT or ex.args[0] == COR_E_SUBSCRIBERS_FAILED:
                    logger.debug('Cath %s exception: \"%s\". Checking timeout...' % (NAMES_of_COR_E[ex.args[0] ], str(ex)))
                    logger.debug(txt_pikuli_search_pattern % txt_search_timeout)
                    if (datetime.datetime.today()-t0).total_seconds() >= timeout:
                        raise FindFailed('%s: Timeout while looking for UIA element:\n\tself = %s\n\tkwargs = %s' % (_func_name, repr(self), str(kwargs)))
                    # t0 = datetime.datetime.today()
                    time.sleep(next_serach_iter_delya)
                else:
                    tb_text = ''.join(traceback.format_list(traceback.extract_tb(sys.exc_info()[2])[1:]))
                    full_text = 'Traceback for error point:\n' + tb_text.rstrip() + '\nError message:\n  ' + type(ex).__name__ + ': ' + str(ex)
                    logger.error(full_text)
                    raise ex

            else:
                # Тут, если ищем один элемент и все никак его не найдем или ищем много элементов:
                if not find_first_only or (find_first_only and (datetime.datetime.today()-t0).total_seconds() >= timeout):
                    break
                # t0 = datetime.datetime.today()
                time.sleep(next_serach_iter_delya)

        # В норме мы тут если ищем все совпадения (если ищем только первое, то должно было произойти и перехватиться исключение FirstFoundEx).
        if find_first_only:
            raise('%s [INTERNAL]: Strange! We should not be here: ' % _func_name + str(getframeinfo(currentframe())))
        if len(found_winuiaelem_arr) == 0:
            if exception_on_find_fail:
                raise FindFailed('%s: no one elements was found\n\tself = %s\n\tkwargs = %s\n\tcriteria = %s' % (_func_name, repr(self), str(kwargs), str__criteria))
            found_elem = []
            # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
            logger.debug(txt_pikuli_search_pattern % ('there has been found no one UI-elem (%s)' % (str(timeout))))
        else:
            found_elem = map(self.__create_instance_of_suitable_class, found_winuiaelem_arr)

            # Сормируем строку для вывода на экран из найденных элементов. Длина строки не более 70 символов.
            if len(found_elem) <= 2:
                s = repr(found_elem)
            else:
                s = repr(found_elem[:2])
                for i in range(3, len(found_elem)):
                    ss = repr(found_elem[:i])
                    if len(ss) > 70:
                        break
                    s = ss
                if 'ss' in locals() and len(s) != len(ss):
                    s = s[:-1] + ', ...]'
            # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
            logger.debug(txt_pikuli_search_pattern % ('there has been found %i UI-elems: %s (%s)' % (len(found_elem), s, str(timeout))))
        return found_elem


    def reg(self, get_client_rect_by_hwnd=False):
        '''
        Возвращает Region для self-элемента HWNDElement.
            -- get_client_rect_by_hwnd = True:  через прстое Win32API запрашвается клиентская часть окна.
               get_client_rect_by_hwnd = False: через UIA запрашивается область элемента. К примеру для обычного окна это область внешней рамки.
                                                То есть прямоуголник зависит от декорирования окна в Windows, так как включается не только клиентская часть.
        '''
        self._test4readiness()

        if get_client_rect_by_hwnd:
            if self.hwnd is None or self.hwnd == 0:
                raise Exception('pikuli.UIElemen.reg(...): \'%s\' has no hwnd, but get_client_rect_by_hwnd = True' % (repr(self)))
            # полчение размеров клменскй области окна
            (_, _, wc, hc) = win32gui.GetClientRect(self.hwnd)
            # получение координат левого верхнего угла клиенской области осносительно угла экрана
            (xc, yc) = win32gui.ClientToScreen(self.hwnd, (0, 0) )
            self._reg = Region.Region(xc, yc, wc, hc, winctrl=self, title=self.Name, find_timeout=self._find_timeout)
        else:
            rect = self._winuiaelem.GetCurrentPropertyValue(UIA.UIA_automation_element_property_identifers_mapping['BoundingRectangle'])
            try:
                rect = map(int, rect)
            except ValueError:
                raise FailExit('pikuli.UIElemen.reg(...): can not round numbers in rect = %s' % str(rect))
            self._reg = Region.Region(*rect, winctrl=self, title=self.Name, find_timeout=self._find_timeout)

        return self._reg

    @property
    def region(self):
        return self.reg()


    def wait_prop_chage(self, prop_name, timeout=None):

        prop_id = UIA.UIA_automation_element_property_identifers_mapping.get(prop_name, None)
        if prop_id is None:
            raise FailExit('...')
        self.__wait_chages__prev_prop = self._winuiaelem.GetCurrentPropertyValue(prop_id)
        wait_while(lambda: self.__wait_chages__prev_prop == self._winuiaelem.GetCurrentPropertyValue(prop_id), timeout)


    def wait_prop_chage_to(self, prop_name, new_val, timeout=None):
        prop_id = UIA.UIA_automation_element_property_identifers_mapping.get(prop_name, None)
        if prop_id is None:
            raise FailExit('...')
        wait_while(lambda: new_val != self._winuiaelem.GetCurrentPropertyValue(prop_id), timeout)


    def wait_appear(self, **kwargs):
        timeout = kwargs.pop('timeout', None)
        return wait_while(lambda: not self.find(**dict(kwargs, exception_on_find_fail=False)), timeout)

    def wait_vanish(self, **kwargs):
        timeout = kwargs.pop('timeout', None)
        return wait_while(lambda: self.find(**dict(kwargs, exception_on_find_fail=False)), timeout)

    def is_existed(self, **kwargs):
        return self.find(**dict(kwargs, exception_on_find_fail=False, timeout=0))

    def _unavaulable_method_dummy(*args, **kwargs):
        raise Exception('_unavaulable_method_dummy: ' + str(args))



class _uielement_Control(UIAElement):

    REQUIRED_PATTERNS = {'LegacyIAccessiblePattern': None}  # То есть, всегда, для всех функций.

    def __init__(self, *args, **kwargs):
        super(_uielement_Control, self).__init__(*args, **kwargs)

        critical_error = False
        methods_to_block = []
        for c in type(self).mro():
            if hasattr(c, 'REQUIRED_PATTERNS'):
                for (pattern, methods) in c.REQUIRED_PATTERNS.items():
                    if self.get_property('Is'+pattern+'Available') is None:
                        logger.warning('[WARNING] pikuli.ui_element: %s should support \'%s\', but it does not. The following methods will be unavalibale: %s' % (str(self), pattern, ' -- ALL --' if methods is None else str(methods)))
                        if methods is None:
                            critical_error = True
                        else:
                            methods_to_block += methods

            if hasattr(c, 'REQUIRED_METHODS'):
                for (req_method, dep_methods) in c.REQUIRED_METHODS.items():
                    if not hasattr(self, req_method):
                        logger.warning('[WARNING] pikuli.ui_element: %s should have %s() method, but it does not. The following dependent methods will be unavalibale: %s' % (str(self), str(req_method), str(dep_methods)))
                        methods_to_block += methods

        if critical_error:
            raise Exception('pikuli.UIAElement: UIAElement Control %s does not support some vital UIA-patterns. See WARNINGs above.' % str(self))

        for m in methods_to_block:
            if not hasattr(self, m):
                logger.warning('[WARNING] pikuli.ui_element: you try to block method \'%s\' by means of unsupported \'%s\' in %s. But this method does not defined in class \'%s\'. Do you have a mistake in definition of \'%s\'?' % (m, pattern, str(self), type(self).__name__, type(self).__name__))
            else:
                setattr(self, m, self._unavaulable_method_dummy)

    def is_unavailable(self):
        return bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['UNAVAILABLE'])

    def is_available(self):
        return (not self.is_unavailable())

    def is_focused(self):
        return bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['FOCUSED'])

    def bring_to_front(self):
        self._test4readiness()
        return hwnd_element.HWNDElement(self).bring_to_front()

    def click(self, method='click', p2c_notif=True):
        '''
            Эмулирует клин мыши на контролле (method='invoke') или действительно подводит курсор и кликает (method='click'). Реальный клик
            будет просто в цетр области, получаемый из метода reg().
            TODO: !!! invoke пока не реализован !!!
        '''
        if method == 'click':
            if hasattr(self, 'scroll_into_view'):
                self.scroll_into_view()

            if hasattr(self, '_type_text_click'):
                click_location = self._type_text_click['click_location']  # к примеру, метод getTopLeft()
                f = getattr(self.region, click_location[0], None)
                if f is None:
                    raise Exception('_Enter_Text_method.type_text(...): [INTERNAL] wrong \'click_location\':\n\t_type_text_click = %s' % str(_type_text_click))
                if click_location[1] is None:
                    loc = f()
                elif click_location[2] is None:
                    loc = f(*click_location[1])
                else:
                    loc = f(*click_location[1], **click_location[2])

                click_method = getattr(loc, self._type_text_click['click_method'], None)
                if click_method is None:
                    raise Exception('_Enter_Text_method.type_text(...): [INTERNAL] wrong \'click_method\':\n\t_type_text_click = %s' % str(_type_text_click))
                click_method(p2c_notif=False)

                if p2c_notif:
                    logger.info('pikuli.{}.click(): click on {} with method "{}" at location {} = {cl[0]}({cl[1]}, {cl[2]})'.format(
                        type(self).__name__, self, self._type_text_click['click_method'], loc, cl=click_location))

            else:
                self.region.click(p2c_notif=False)
                if p2c_notif:
                    logger.info('pikuli.%s.click(): click in center of %s' % (type(self).__name__, str(self)))
        else:
            raise Exception('pikuli.%s.click(): unsupported method = \'%s\'' % (type(self).__name__, str(method)))



class _ValuePattern_methods(UIAElement):

    REQUIRED_PATTERNS = {'ValuePattern': ['get_value', 'set_value_api', 'is_readoly']}

    def get_value(self):
        return _None_of_str(self.get_pattern('ValuePattern').CurrentValue)

    def set_value_api(self, text, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        '''
        Возвращает:
            -- True, если состяние контрола изменилось.
            -- False, если не пришлось менять состояние контрола.
            -- None можно оставить на перспективу возникновения исключения и exception_on_find_fail=False
        '''
        text = str(text)
        if self.get_pattern('ValuePattern').CurrentValue != text:
            self.get_pattern('ValuePattern').SetValue(text)
            if not wait_while_not(lambda: self.get_pattern('ValuePattern').CurrentValue == text, check_timeout):
                raise Exception('_ValuePattern_methods.set_value_api(...): valur is still %s, not %s after %s seconds' % (str(self.get_pattern('ValuePattern').CurrentValue), text, str(check_timeout)))
            changed = True
        else:
            changed = False
        if p2c_notif:
            if changed:
                logger.info('pikuli.%s.set_value_api(): set \'%s\' to %s (via ValuePattern)' % (type(self).__name__, repr(text), str(self)))
            else:
                logger.info('pikuli.%s.set_value_api(): \'%s\' is alredy in %s (via ValuePattern)' % (type(self).__name__, repr(text), str(self)))
        return changed

    def is_readoly(self):
        return bool(self.get_pattern('ValuePattern').CurrentIsReadOnly)



class _LegacyIAccessiblePattern_value_methods(UIAElement):

    def get_value(self):
        return self.get_pattern('LegacyIAccessiblePattern').CurrentValue

    def set_value_api(self, text, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        '''
        Возвращает:
            -- True, если состяние контрола изменилось.
            -- False, если не пришлось менять состояние контрола.
            -- None можнооставить на перспективу возникновения исключения и exception_on_find_fail=False
        '''
        text = str(text)
        if self.get_pattern('LegacyIAccessiblePattern').CurrentValue != text:
            self.get_pattern('LegacyIAccessiblePattern').SetValue(text)
            if not wait_while_not(lambda: self.get_pattern('LegacyIAccessiblePattern').CurrentValue == text, check_timeout):
                raise Exception('_LegacyIAccessiblePattern_value_methods.set_value_api(...): value is still %s, not %s after %s seconds' % (str(self.get_pattern('LegacyIAccessiblePattern').CurrentValue), text, str(check_timeout)))
            changed = True
        else:
            changed = False
        if p2c_notif:
            if changed:
                logger.info('pikuli.%s.set_value_api(): set \'%s\' to %s (via LegacyIAccessiblePattern)' % (type(self).__name__, repr(text), str(self)))
            else:
                logger.info('pikuli.%s.set_value_api(): \'%s\' is alredy in %s (via LegacyIAccessiblePattern)' % (type(self).__name__, repr(text), str(self)))
        return changed



TEXT_CLEAN_METHODS = ['uia_api', 'end&backspaces', 'home&deletes', 'single_backspace']

class _Enter_Text_method(UIAElement):

    REQUIRED_METHODS = {'get_value': ['type_text', 'enter_text'], 'set_value_api': ['type_text', 'enter_text']}
    _type_text_click = {'click_method': 'click', 'click_location': ('getCenter', None, None), 'enter_text_clean_method': 'end&backspaces'}


    def paste_text(self, text, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        """ Обязательно кликнет, а затем сделат Ctrl+V. Удаления или выделения старого текста нет! """
        buff = get_text_from_clipboard()
        try:
            set_text_to_clipboard(text)
            self.click()
            self.type_text('v', modifiers=KeyModifier.CTRL)
        except:
            raise
        finally:
            set_text_to_clipboard(buff)

    def clear_text(self, clean_method, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        if clean_method is None:
            clean_method = self._type_text_click.get('enter_text_clean_method', None)
        if clean_method is None:
            raise Exception('_Enter_Text_method.enter_text(...): clean_method = None, but self._type_text_click does not contain \'enter_text_clean_method\' field\n\tself._type_text_click = %s' % str(self._type_text_click))

        if clean_method == 'uia_api':
            if hasattr(self, 'set_value_api'):
                self.set_value_api('')
            else:
                raise Exception('_Enter_Text_method.clear_text(...): clean_method = \'%s\', but control \'%s\' does not support \'set_value_api()\' method.' % str(clean_method, str(type(self))))
        elif clean_method == 'end&backspaces':
            self.type_text(Key.END + Key.BACKSPACE*(len(self.get_value())+1), chck_text=False, click=True, p2c_notif=False)
        elif clean_method == 'home&deletes':
            self.type_text(Key.HOME + Key.DELETE*(len(self.get_value())+1), chck_text=False, click=True, p2c_notif=False)
        elif clean_method == 'single_backspace':
            self.type_text(Key.BACKSPACE, chck_text=False, click=True, p2c_notif=False)
        elif clean_method in TEXT_CLEAN_METHODS:
            raise Exception('_Enter_Text_method.clear_text(...): [ITERNAL] [TODO] clean_method = \'%s\' is valid, but has not been realised yet.' % str(clean_method))
        else:
            raise Exception('_Enter_Text_method.clear_text(...): clean_method = {!r}'.format(clean_method))

    def type_text(self, text, modifiers=None, chck_text=False, click=True, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        '''
        Кликнем мышкой в _type_text_click, если click=True, и наберем новый текст без автоматического нажания ENTER'a.
        Результат набора текста по умолчанию проверяется -- за это ответчает агрумент chck_text:
            - chck_text = None     - ожидаем, что туда, куда ввели текст, будет text
            - chck_text = False    - не проверяем, какой текст ввелся
            - chck_text = <строка> - сверяем оставшийся текст со <строка>

        При необходимости надо переопределять _type_text_click в дочерних класах, т.к. кликать, возможно, нужно будет не в центр.
        Структура _type_text_click:
            - имя метода у объекта, возвращаемого self.region
            - args как список (list) для этой функции или None
            - kwargs как словарь (dict) для этой функции или None
        '''
        text = str(text)

        if click:
            self.click()
        type_text(text, modifiers=modifiers)

        if not (chck_text == False):
            if chck_text is None:
                chck_text = text
            if not wait_while_not(lambda: self.get_value() == str(chck_text), check_timeout):
                raise Exception('_Enter_Text_method.type_text(...): text is still %s, not %s after %s seconds' % (self.get_value(), repr(chck_text), str(check_timeout)))

        if p2c_notif:
            logger.info('pikuli.%s.type_text(): type \'%s\' in %s' % (type(self).__name__, repr(text), str(self)))


    def enter_text(self, text, method='click', clean_method=None, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        '''
        Перезапишет текст в контроле.
        В качестве значения method могут быть:
            -- click  - Кликнем мышкой по строке и введем новый текст c автоматическим нажания ENTER'a. Используется type_text().
            -- invoke - Через UIA. Используется set_value_api().
        clean_method:
            -- None - использовать из структуры self._type_text_click
            -- Одно из значений TEXT_CLEAN_METHODS = ['uia_api', 'end&backspaces', 'home&deletes', 'single_backspace']

        Возвращает:
            -- True, если состяние контрола изменилось.
            -- False, если не пришлось менять состояние контрола.
            -- None можнооставить на перспективу возникновения исключения и exception_on_find_fail=False
        '''
        text = str(text)
        if method == 'click':
            if text != self.get_value():
                #self.type_text('a', modifiers=KeyModifier.CTRL, chck_text=False, click=True) -- не на всех контролах корректно работает
                self.clear_text(clean_method, check_timeout=check_timeout, p2c_notif=p2c_notif)

                #if len(self.get_value()) != 0:  --  а если поле не поддается очищению, а сосдение -- очищается (пример: "гриды")? Лучше првоерку убрать -- важен еонечный результа.
                #    raise Exception('_Enter_Text_method.enter_text(...): can not clear the text field. It still contains the following: %s' % self.get_value())
                self.type_text(text + Key.ENTER, chck_text=False, click=False, p2c_notif=False)
                changed = True
            else:
                changed = False
        elif method == 'invoke':
            changed = self.set_value_api(text, p2c_notif=False)
        else:
            raise Exception('_Enter_Text_method.enter_text(...): unsupported method = \'%s\'' % str(method))

        if p2c_notif:
            if changed:
                logger.info('pikuli.%s.enter_text(): enter \'%s\' in %s' % (type(self).__name__, repr(text), str(self)))
            else:
                logger.info('pikuli.%s.enter_text(): \'%s\' is alredy in %s' % (type(self).__name__, repr(text), str(self)))
        return changed


class Desktop(UIAElement):
    '''
    Represents the Desktop. Creating an instance of this class is equal to UIAElement(0).
    '''
    def __init__(self):
        super(Desktop, self).__init__(0)


class CustomControl(UIAElement):
    """
    Cunstom (Graphic, for example) control. It does not support LegacyIAccessiblePattern, because this patternt
    adds to provider by Windows only for navire controls. But for all native ones.
    """

    CONTROL_TYPE = 'Custom'


class Window(_uielement_Control):

    CONTROL_TYPE = 'Window'



class Pane(_uielement_Control):

    CONTROL_TYPE = 'Pane'




class Button(_uielement_Control):

    CONTROL_TYPE = 'Button'

    def is_avaliable(self):
        return not bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['UNAVAILABLE'])

    def is_unavaliable(self):
        return bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['UNAVAILABLE'])





class CheckBox(_uielement_Control):

    CONTROL_TYPE = 'CheckBox'
    REQUIRED_PATTERNS = {}

    TOOGLE_STATES_TO_BOOL = {
        UIA.UIA_wrapper.ToggleState_On: True,
        UIA.UIA_wrapper.ToggleState_Off: False,
        UIA.UIA_wrapper.ToggleState_Indeterminate: None
    }

    def _state(self, method):
        """
        Получаем состояние CheckBox (установлена ли галочка).

        :return: `True`, `False`, `None` (если `ToggleState_Indeterminate` через UIA)
        """
        if method in ['click', 'legacy']:
            curr_state = self.get_pattern('LegacyIAccessiblePattern').CurrentState
            state = bool(curr_state & STATE_SYSTEM['CHECKED'])
        elif method == 'uia':
            toog_state = self.get_pattern('TogglePattern').CurrentToggleState
            state = self.TOOGLE_STATES_TO_BOOL[toog_state]
        else:
            raise Exception('CheckBox.check(...): unsupported method = \'{}\''.format(method))
        return state

    def _uia_toogle(self):
        """
        Вызывает метод Toogle из TogglePattern. Важно помнить, что может быть 2 или 3 состояния,
        которые этим методом циклически переключаются
        (см. https://msdn.microsoft.com/en-us/library/windows/desktop/ee671459(v=vs.85).aspx)
        """
        res = self.get_pattern('TogglePattern').Toggle()
        # TODO: assert res == UIA.UIA_wrapper.S_OK, 'Toggle res = {}'.format(res)  --  нужен код S_OK.

    def _check_state(self, expected_state, method):
        """
        Проверяем состояние CheckBox (установлена ли галочка).

        :param bool expected_state: Ожидаемое состояние CheckBox (`True` -- галочка установлена)
        :param str method: Метод проверки: `legacy` -- через `LegacyIAccessiblePattern`, а `uia` --
                           через `TogglePattern`.
        """
        state = self._state(method)
        return expected_state is state

    def _change_state_to(self, target_state, method, check_timeout):
        """
        Изменением состояние CheckBox на желаемое.

        :param bool target_state: Желаемое состояние CheckBox (`True` -- галочка установлена)
        :param str method: Метод проверки: `click` -- через клик в центр контрола, а `uia` --
                           через `TogglePattern`.
        """
        # Если уже, где надо, то просто выходим:
        if self._check_state(target_state, method):
            return False

        # Меняем состояние:
        if method == 'click':
            self.region.click()

        else:  # Метод 'uia':
            init_state = self._state('uia')
            self._uia_toogle()

            # Ждем смены состояния на новое:
            if not wait_while(lambda: self._check_state(init_state, 'uia'), check_timeout):
                raise Exception('CheckBox.uncheck(...): error change state to {}: init = {}, current = {} (timeout {})'.foramt(
                    target_state, init_state, self._state('uia'), check_timeout))

            # Если сменилось на новое, но не желаемое, значит состояний три и надо еще раз Toogle():
            if not self._check_state(target_state, 'uia'):
                self._uia_toogle()

        # Дожидаемся жалаемого состояния:
        if not wait_while_not(lambda: self._check_state(target_state, method), check_timeout):
            raise Exception('CheckBox.uncheck(...): checkbox is still {} after {} seconds'.format(
                self._state(method), check_timeout))

        return True

    def is_checked(self):
        return self._check_state(True, 'legacy')

    def is_unchecked(self):
        return self._check_state(False, 'legacy')

    def check(self, method='click', check_timeout=CONTROL_CHECK_TIMEOUT):
        """
        Потенциально в качестве значения method могут быть click (подвести курсов мыши и кликнуть) или invoke (через UIA).
        Возвращает:
            -- True, если состяние контрола изменилось.
            -- False, если не пришлось менять состояние контрола.
            -- None можнооставить на перспективу возникновения исключения и exception_on_find_fail=False
        """
        return self._change_state_to(True, method, check_timeout)

    def uncheck(self, method='click', check_timeout=CONTROL_CHECK_TIMEOUT):
        """
        см. описание :func:`CheckBox.check`.
        """
        return self._change_state_to(False, method, check_timeout)

    def check_or_uncheck(self, check_bool, method='click', check_timeout=CONTROL_CHECK_TIMEOUT):
        """
        см. описание :func:`CheckBox.check`.
        """
        if check_bool:
            return self.check(method=method, check_timeout=check_timeout)
        else:
            return self.uncheck(method=method, check_timeout=check_timeout)



class Edit(_uielement_Control, _ValuePattern_methods, _Enter_Text_method):

    CONTROL_TYPE = 'Edit'
    REQUIRED_PATTERNS = {}



class Text(_uielement_Control, _ValuePattern_methods):

    CONTROL_TYPE = 'Text'
    REQUIRED_PATTERNS = {}



class ComboBox(_uielement_Control, _ValuePattern_methods, _Enter_Text_method):

    """
    Методы:
        select_item    --  Мышкой выбирает элемент из выпадающего меню.
        set_value_api  --  Через UIA API выставить новое значение (метод из _ValuePattern_methods).
        get_value      --  Переопредеялем метод из _ValuePattern_methods.
    """

    CONTROL_TYPE = 'ComboBox'
    REQUIRED_PATTERNS = {}

    def list_items(self):
        '''
            Если меню открыто, то вренут списко объектов, описывающих каждый пункт меню (теоретически, это может быть пустой список).
            Если меню закрыто, то вернет None.
        '''
        l = self.find(ControlType='List', exact_level=1, exception_on_find_fail=False, timeout=1)
        if l is None:
            return None
        return l.list_items()

    """def name_of_choosed(self):  --  есть метод _ValuePattern_methods.get_value()
        ''' Вернет тектсовую строку того пукта выпдающего меню, который выбран. '''
        return self.find(ControlType='Text', exact_level=1).get_value()"""

    def get_item_by_name(self, item_name):
        """
        Если список ракрыт, то вернут подходящий объект ListItem. Если объекта не нашлось в списке в течение timeout, то будет исключение
        :param item_name: название поля
        """
        item_name = str(item_name)
        if self.list_items() is None:
            raise FindFailed('List of ComboBox %s was not found. Is this list collapsed?' % repr(self))
        if wait_while_not(lambda: any(item_name in str(s) for s in self.list_items()), CONTROL_CHECK_TIMEOUT):
            items = [i for i in self.list_items() if i.Name == item_name]
            assert len(items) == 1  # Не меньше и не больше одного
            return items[0]
        else:
            raise FindFailed('ComboBox item was not show for timeout {}'.format(CONTROL_CHECK_TIMEOUT))

    def select_item(self, item_name):
        """
        Выбрать пункт.
            item_name  --  строка, содержащая текст делаемого пункта выпалдающего меню.
        """
        item_name = str(item_name)
        if self.get_value() != item_name:
            if self.list_items() is None:
                self.click()
            self.get_item_by_name(item_name).click()

    def get_value(self):
        '''
        У нас комбобоксы бывают следующих типов:
            <text> + <Open button>
            <edit> + <Open button>
            <edit> + <spiner>
        Может сложиться ситуация, когда Value всего комбобокса пустое, а Value у <edit> -- нет. И как раз этот дочерний объект и содержит искомые данные.

        Переопределяем функцию из _ValuePattern_methods. Делаем так:
            -- если value_cmbbox == '', то возвращаем value_child
            -- если value_cmbbox == value_child, то возвращаем это
            -- если value_cmbbox != value_child и value_cmbbox != '', то генерируем исключение
        '''
        value_cmbbox = _None_of_str(self.get_pattern('ValuePattern').CurrentValue)

        childs = self.find_all(ControlType='Text', exact_level=1) + self.find_all(ControlType='Edit', exact_level=1)
        if len(childs) > 1:
            raise Exception('ComboBox.get_value(...): there are more than one \'Text\' or/and \'Edit\' child controls:\n\tchilds = %s' % str(childs))
        value_child = childs[0].get_value()

        # Есть сам комбо-бокс, а есть его дочерний объект. Бывает, что комбо-бокс возрвращает путоту -- тогда данные надо брыть у дочернего объекта.
        # Комбобокс, теоретически, может и пустую строку возвращать.
        if value_cmbbox is None  or  value_cmbbox == '' and value_child != '':
            return value_child
        elif value_cmbbox != value_child:
            raise Exception('ComboBox.get_value(...): values of ComboBox-self and its child Text or Edit object differ:\n\tvalue_cmbbox = %s\n\tvalue_child = %s' % (value_cmbbox, value_child))
        else:
            return value_cmbbox



class Tree(_uielement_Control):

    CONTROL_TYPE = 'Tree'
    REQUIRED_PATTERNS = {} # {'SelectionPattern': []}

    def __init__(self, *args, **kwargs):
        super(Tree, self).__init__(*args, **kwargs)
        self._last_tree = []

    def get_current_tree(self):
        ''' Дерево вида:
        [
            (<TreeItem>, [
                <TreeItem>, [...],  # если узел развернут (включая частичное разворачивание)
                <TreeItem>, [],     # если узел полностью свернут
                <TreeItem>, None    # если нет дочерних узелков
            ]),
            (<TreeItem>, []),
            (<TreeItem>, None),
            ...
        ]
        Если дерево пусто, то вернется None (не пустой список []).
        '''

        def _next_node(treeitem):
            if not treeitem.is_expandable():
                # Если нет ветви, идущей из этого "узелка":
                branch = None
            else:
                # Если есть такая ветвь:
                childs = treeitem.find_all(exact_level=1)
                branch = map(_next_node, childs)
            return (treeitem, branch)

        self._last_tree = []
        for treeitem in self.find_all(exact_level=1):
            self._last_tree.append(_next_node(treeitem))

        return self._last_tree

    """def get_first_item(self):
        return self.find(exact_level=1)"""

    def list_current_subitems(self):
        ''' Вернут список дочерних узелков (1 уровень вложенности). Вернет None, если нет дочерних узелков. '''
        items = self.find_all(exact_level=1, ControlType='TreeItem')
        if len(items) == 0:
            return None
        return items

    def find_item(self, item_name, force_expand=False, timeout=None, exception_on_find_fail=True):
        '''
            item_name -- Cписок строк-названий эелементов дерева, пречисленных по их вложенности один в другой. Последняя строка в списке -- искомый элемент.
            force_expand -- разворачивать ли свернутые элементы на пути поиска искового.
        '''
        # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
        logger.debug('pikuli.Tree.find_item: searching by criteria item_name = \'%s\', timeout = %s' % (str(item_name), str(timeout)))

        if isinstance(item_name, str):
            item_name = [item_name]
        if not isinstance(item_name, list):
            raise Exception('pikuli.ui_element.Tree: not isinstance(item_name, list) and not isinstance(item_name, str)\n\titem_name = %s\n\ttimeout = %s' % (str(item_name), str(timeout)))

        if len(item_name) == 0:
            raise Exception('pikuli.ui_element.Tree: len(item_name) == 0')
        else:
            elem = self.find(Name=item_name[0], exact_level=1, ControlType='TreeItem', timeout=timeout, exception_on_find_fail=exception_on_find_fail)
            if elem is None:
                logger.debug('pikuli.ui_element.Tree.find_item: %s has not been found. No exception -- returning None' % str(item_name))
                return None
            if len(item_name) == 1:
                found_elem = elem
            else:
                found_elem = elem.find_item(item_name[1:], force_expand, timeout=timeout, exception_on_find_fail=exception_on_find_fail)

        """
        TODO: не работает пауза: сразу содает несолкьо анализов ситацайии, не дожидаясь появления первого
        else:
            elem = self.find_all(Name=item_name[0], exact_level=1, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
            if (elem is None) or (len(elem) == 0):
                if exception_on_find_fail:
                    logger.error('pikuli.ui_element.Tree.find_item: \'%s\' has not been found. Raising exception...' % str(item_name))
                    raise Exception('pikuli.ui_element.Tree.find_item: \'%s\' has not been found.' % str(item_name))
                else:
                    logger.error('pikuli.ui_element.Tree.find_item: \'%s\' has not been found. No exception -- returning None' % str(item_name))
                    return None
            if len(elem) != 1:
                if exception_on_find_fail:
                    logger.error('pikuli.ui_element.Tree.find_item: more than one elemnt \'%s\' has been found. Raising exception...' % str(item_name))
                    raise Exception('pikuli.ui_element.Tree: more than one elemnt \'%s\' has been found.' % str(item_name))
                else:
                    logger.error('pikuli.ui_element.Tree.find_item: more than one elemnt \'%s\' has been found. No exception -- returning None' % str(item_name))
                    return None

            if len(item_name) == 1:
                found_elem = elem[0]
            else:
                found_elem = elem[0].find_item(item_name[1:], force_expand, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
        """

        return found_elem


class TreeItem(CheckBox, _uielement_Control):
    """
    Наследование от :class:`CheckBox` здесь чисто утилитарное -- нужные его методы.
    """

    CONTROL_TYPE = 'TreeItem'
    REQUIRED_PATTERNS = {
        'SelectionItemPattern': ['is_selected'],
        'ExpandCollapsePattern': ['is_expandable', 'is_expanded', 'is_collapsed', 'expand', 'collapse'],
        'ScrollItemPattern': ['scroll_into_view'],
        'TogglePattern': ['is_unchecked', 'is_checked', 'uncheck', 'check', 'check_or_uncheck']
    }

    def is_selected(self):
        return bool(self.get_pattern('SelectionItemPattern').CurrentIsSelected)

    def is_expandable(self):
        return not (self.get_pattern('ExpandCollapsePattern').CurrentExpandCollapseState == UIA.UIA_wrapper.ExpandCollapseState_LeafNode)

    def is_expanded(self):
        ''' Проверка, что развернут текущий узел (полностью, не частично). Без учета состояния дочерних узлов. Если нет дочерних, то функция вернет False. '''
        if not self.is_expandable():
            return False
        return (self.get_pattern('ExpandCollapsePattern').CurrentExpandCollapseState == UIA.UIA_wrapper.ExpandCollapseState_Expanded)

    def is_collapsed(self):
        ''' Проверка, что развернут текущий узел (полностью, не частично). Без учета состояния дочерних узлов. Если нет дочерних, то функция вернет True. '''
        if not self.is_expandable():
            return True
        return (self.get_pattern('ExpandCollapsePattern').CurrentExpandCollapseState == UIA.UIA_wrapper.ExpandCollapseState_Collapsed)

    def expand(self):
        if self.is_expandable() and not self.is_expanded():
            self.get_pattern('ExpandCollapsePattern').Expand()
        if not self.is_expanded():
            raise Exception('pikuli.ui_element: can not expand TreeItem \'%s\'' % self.Name)

    def collapse(self):
        if self.is_expandable() and not self.is_collapsed():
            self.get_pattern('ExpandCollapsePattern').Collapse()
        if not self.is_collapsed():
            raise Exception('pikuli.ui_element: can not collapse TreeItem \'%s\'' % self.Name)

    def scroll_into_view(self):
        self.get_pattern('ScrollItemPattern').ScrollIntoView()

    def list_current_subitems(self, force_expand=False):
        ''' Вернут список дочерних узелков (1 уровень вложенности), если текущий узел развернут. Вернет [], если узел свернут полностью или частично. Вернет None, если нет дочерних узелков. '''
        if not self.is_expandable():
            return None
        if not self.is_expanded():
            if force_expand:
                self.expand()
            else:
                logger.warning('Node {} is collapsed, but force_expand = {}'.format(self, force_expand))
        if self.is_expanded():
            return self.find_all(ControlType='TreeItem', exact_level=1)
        return []

    def find_item(self, item_name, force_expand=False, timeout=None, exception_on_find_fail=True):
        '''
            item_name -- Cписок строк-названий эелементов дерева, пречисленных по их вложенности один в другой. Последняя строка в списке -- искомый элемент.
            force_expand -- разворачивать ли свернутые элементы на пути поиска искового.
        '''
        # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
        logger.debug('pikuli.TreeItem.find_item: searching by criteria item_name = \'%s\', timeout = %s' % (str(item_name), str(timeout)))

        if isinstance(item_name, str):
            item_name = [item_name]
        if not isinstance(item_name, list):
            raise Exception('pikuli.ui_element.TreeItem: not isinstance(item_name, list) and not isinstance(item_name, str);\n\titem_name = %s\n\ttimeout = %s' % (str(item_name), str(timeout)))
        if len(item_name) == 0:
            raise Exception('pikuli.ui_element.TreeItem: len(item_name) == 0')
        if not self.is_expanded() and not force_expand:
            raise FindFailed('pikuli.ui_element.TreeItem: item \'%s\' was found, but it is not fully expanded. Try to set force_expand = True.\nSearch arguments:\n\titem_name = %s\n\tforce_expand = %s' % (self.Name, str(item_name), str(force_expand)))

        self.expand()

        elem = self.find(Name=item_name[0], ControlType='TreeItem', exact_level=1, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
        if elem is None:
            logger.debug('pikuli.ui_element.TreeItem.find_item: %s has not been found. No exception -- returning None' % str(item_name))
            return None
        if len(item_name) == 1:
            found_elem = elem
        else:
            found_elem = elem.find_item(item_name[1:], force_expand, timeout=timeout)

        """
        TODO: не работает пауза: сразу содает несолкьо анализов ситацайии, не дожидаясь появления первого
        elem = self.find_all(Name=item_name[0], exact_level=1, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
        if (elem is None) or (len(elem) == 0):
            if exception_on_find_fail:
                logger.error('pikuli.ui_element.TreeItem.find_item: \'%s\' has not been found. Raising exception...' % str(item_name))
                raise Exception('pikuli.ui_element.TreeItem.find_item: \'%s\' has not been found.' % str(item_name))
            else:
                logger.error('pikuli.ui_element.TreeItem.find_item: \'%s\' has not been found. No exception -- returning None' % str(item_name))
                return None
        if len(elem) != 1:
            if exception_on_find_fail:
                logger.error('pikuli.ui_element.TreeItem.find_item: more than one elemnt \'%s\' has been found. Raising exception...' % str(item_name))
                raise Exception('pikuli.ui_element.TreeItem: more than one elemnt \'%s\' has been found.' % str(item_name))
            else:
                logger.error('pikuli.ui_element.TreeItem.find_item: more than one elemnt \'%s\' has been found. No exception -- returning None' % str(item_name))
                return None

        if len(item_name) == 1:
            found_elem = elem[0]
        else:
            found_elem = elem[0].find_item(item_name[1:], force_expand, timeout=timeout)
        """

        return found_elem


class ANPropGrid_Table(_uielement_Control):
    '''
    Таблица настроек в AxxonNext ничего не поддерживает, кроме Legacy-паттерна.
    Считаем, что таблицы из двух колонок. Левая колонка в каждой строке всегда заполнена. Правая может иметь или не иметь значения.
    '''

    CONTROL_TYPE = 'Table'

    def __init__(self, *args, **kwargs):
        super(ANPropGrid_Table, self).__init__(*args, **kwargs)
        self._last_tree = []

    def get_curretnn_table(self):
        '''
        Вернуть словарь-дерево строк не поулчится, т.к. все строки, даже вложенные под другую, отображаются как плоский список дочерних элементов таблицы.
        Все строки в UIA "сестры" и между ними нет связи "родитель-потомки". Таблица -- непосредственный родитель для всех своих строк.
        Поэтому возвращаем просой список:
            [<Row>, <Row>, ...]
        '''
        return self.find_all(exact_level=1)

    def find_row(self, row_name, force_expand=False):
        ''' Если row_name:
            a) str или unicode, то это просто имя строки таблицы
            б) если список, то в нем перечислены вложения строк таблицы. Последняя в списке -- искомая строка.

            force_expand -- разворачивать ли свернутые строки, если они обнаружены при поиске строки и являются для нее группирующими.
        '''
        def _find_row_precisely(obj, nested_name, exact_level):

            rows = [e for e in obj.find_all(Name=nested_name, exact_level=exact_level) if isinstance(e, ANPropGrid_Row)]
            if len(rows) > 1:
                Exception('ANPropGrid_Table.find_row._find_row_precisely(...): len(rows) != 0\n\tlen(rows) = %i\n\trows = %s' % (len(rows), str(rows)))
            elif len(rows) == 0:
                raise FindFailed('pikuli.ANPropGrid_Table: row \'%s\' not found.\nSearch arguments:\n\trow_name = %s\n\tforce_expand = %s' % (str(nested_name), str(row_name), str(force_expand)))
            return rows[0]
        # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
        logger.debug('pikuli.ANPropGrid_Table.find_row: searching by criteria item_name = \'%s\'' % str(row_name))
        if isinstance(row_name, list):
            row = _find_row_precisely(self, row_name[0], 1)
            for nested_name in row_name[1:]:
                if not row.is_expanded() and not force_expand:
                    raise FindFailed('pikuli.ANPropGrid_Table: row \'%s\' was found, but it is collapsed. Try to set force_expand = True.\nSearch arguments:\n\trow_name = %s\n\tforce_expand = %s' % (str(nested_name), str(row_name), str(force_expand)))
                row.expand()
                row = _find_row_precisely(row, nested_name, 0)  # Раньше: Так функция сперва изет Next, а потом -- Previous. Т.о., максимальная скорость (если строки не найдется, то фейл теста -- можно и потратить время на previous-поиск)
            found_elem = row
        else:
            found_elem = _find_row_precisely(self, row_name, 1)
        # logger.debug('pikuli.ANPropGrid_Table.find_row: \'%s\' has been found: %s' % (str(row_name), repr(found_elem)))
        return found_elem



class ANPropGrid_Row(_uielement_Control, _LegacyIAccessiblePattern_value_methods, _Enter_Text_method):
    ''' Таблица настроек в AxxonNext ничего не поддерживает, кроме Legacy-паттерна.
    Каждая строка может группировать нижеидущие строки, но в UIA они "сестры", а не "родитель-потомки". Каждая строка можеть иметь или не иметь значения. '''

    CONTROL_TYPE = 'Custom'
    LEGACYACC_ROLE = 'ROW'  # Идентификатор из ROLE_SYSTEM
    _type_text_click = {'click_method': 'click', 'click_location': ('getTopLeft', (30,1), None), 'enter_text_clean_method': 'single_backspace'}

    def has_subrows(self):
        current_state = self.get_pattern('LegacyIAccessiblePattern').CurrentState
        return bool(current_state & STATE_SYSTEM['EXPANDED'] | current_state & STATE_SYSTEM['COLLAPSED'])

    def is_expanded(self):
        ''' Если трока не имеет дочерних, то функция вернет False. '''
        return (self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['EXPANDED'])

    def is_collapsed(self):
        ''' Если трока не имеет дочерних, то функция вернет False. '''
        return (self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['COLLAPSED'])

    """def list_current_subrows(self):
        ''' Вернут список дочерних строк (1 уровень вложенности), если текущая строка развернута. Вернет [], если строка свернута. Вернет None, если нет дочерних строк. '''

        if not self.has_subrows():
            return None
        return self.find_all(exact_level=1)"""

    def expand(self):
        if self.is_collapsed():
            self.get_pattern('LegacyIAccessiblePattern').DoDefaultAction()
        if not self.is_expanded():
            raise Exception('pikuli.ANPropGrid_Row.expand: string \'%s\' was not expanded.' % self.Name)

    def collapse(self):
        if self.is_expanded():
            self.get_pattern('LegacyIAccessiblePattern').DoDefaultAction()
        if not self.is_collapsed():
            raise Exception('pikuli.ANPropGrid_Row.expand: string \'%s\' was not collapsed.' % self.Name)

    """def type_text(self, text):
        ''' Кликнем мышкой по строке и введем новый текст без автоматического нажания ENTER'a.
        Клик мышкой в область с захардкоженным смещением, к сожалению -- иначе можно попасть в вертикальный разделитель колонок. '''
        self.region.getTopLeft(30,1).click()
        type_text(text)"""

    @property
    def value(self):
        return self.get_pattern('LegacyIAccessiblePattern').CurrentValue

    def set_value(self, value):
        self.get_pattern('LegacyIAccessiblePattern').SetValue(value)


class List(_uielement_Control):
    ''' Некий список из ListItem'ов. '''

    CONTROL_TYPE = 'List'

    def list_items(self):
        return self.find_all(ControlType='ListItem', exact_level=1)


class ListItem(_uielement_Control):
    ''' Элементы списка ListItem. '''

    CONTROL_TYPE = 'ListItem'

    def select(self):
        self.get_pattern('SelectionItemPattern').Select()

    @property
    def is_selected(self):
        return bool(self.get_pattern('SelectionItemPattern').CurrentIsSelected)

    @property
    def is_checked(self):
        return self.get_pattern('TogglePattern').CurrentToggleState == UIA.UIA_wrapper.ToggleState_On


class Menu(_uielement_Control):
    ''' Контекстное меню, к примеру. Состоит из MenuItem. '''

    CONTROL_TYPE = 'Menu'

    def list_items(self):
        return self.find_all(ControlType='MenuItem', exact_level=1)

    def find_item(self, item_name, exception_on_find_fail=True):
        return self.find(Name=item_name, ControlType='MenuItem', exact_level=1, exception_on_find_fail=exception_on_find_fail)


class MenuItem(_uielement_Control):
    ''' Контекстное меню, к примеру. '''

    CONTROL_TYPE = 'MenuItem'


class UIAControlType(object):
    '''
    класс обертка над UIA_automation_control_type_identifiers_mapping
    '''

    class __metaclass__(type):
        def __getattr__(cls, key):
            controls = UIA.UIA_automation_control_type_identifiers_mapping
            if key not in controls:
                raise AttributeError(key)
            return controls[key]


locals_keys = locals().keys()
CONTROLS_CLASSES = [i for i in locals_keys if isclass(locals()[i]) and issubclass(locals()[i], _uielement_Control) and locals()[i] != _uielement_Control and (hasattr(locals()[i], 'CONTROL_TYPE') or hasattr(locals()[i], 'ROLE_SYSTEM'))]
