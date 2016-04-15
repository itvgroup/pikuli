# -*- coding: utf-8 -*-

import psutil
from inspect import currentframe, getframeinfo, isclass
import time
import datetime
import traceback
import sys

import _ctypes
import win32gui

import UIA
import Region
from _functions import p2c, wait_while, Key, type_text
from _exceptions import *
import hwnd_element
from oleacc_h import *

# "A lot of HRESULT codes…" (https://blogs.msdn.microsoft.com/eldar/2007/04/03/a-lot-of-hresult-codes/)
COR_E_TIMEOUT = -2146233083  # -2146233083 =<математически>= -0x80131505;   0x80131505 =<в разрядной сетке>= (-2146233083 & 0xFFFFFFFF)
COR_E_SUBSCRIBERS_FAILED = -2147220991  # -2147220991 =<математически>= -0x80040201;
NAMES_of_COR_E = {
    COR_E_TIMEOUT: 'COR_E_TIMEOUT',
    COR_E_SUBSCRIBERS_FAILED: 'COR_E_SUBSCRIBERS_FAILED'
}


# TIMEOUT_UIA_ELEMENT_SEARCH = 30
DEFAULT_FIND_TIMEOUT = 10


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
                argument_type = "UIElement"
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
            2. If required argument is "POINTER(IUIAutomationElement)", we accept UIElement object,
               get required pointer object from UIElement, and send it to function
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
                        argument_type = "UIElement"
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



def _create_instance_of_suitable_class(winuielem):
    winuielem_ControlType = UIA.get_property_by_id(winuielem, 'ControlType')
    winuielem_CurrentRole = UIA.get_pattern_by_id(winuielem, 'LegacyIAccessiblePattern').CurrentRole
    class_by_controltype = class_by_legacy = None

    for class_ in CONTROLS_CLASSES:
        # Очередной анализируемый класс имеет следующие поля:
        class_control_type           = getattr(globals()[class_], 'CONTROL_TYPE', None)
        class_legacy_accessible_role = getattr(globals()[class_], 'LEGACYACC_ROLE', None)

        if class_control_type is None:
            raise Exception('pikuli.UIElement [INTERNAL]: CONTROL_TYPE is not setted for <class %s>. Processing controll \'%s\'' % (class_, UIElement(winuielem).Name))

        elif class_control_type != 'Custom' and winuielem_ControlType != UIA.UIA_automation_control_type_identifiers_mapping['Custom']:
            class_control_type_id = UIA.UIA_automation_control_type_identifiers_mapping.get(class_control_type, None)  # Ищем тип class_control_type среди известных нам.
            if class_control_type_id is None:
                raise Exception('pikuli.UIElement [INTERNAL]: CONTROL_TYPE = \'%s\' in <class %s> is unknown.Processing controll \'%s\'' % (class_control_type, class_, UIElement(winuielem).Name))
            if winuielem_ControlType == class_control_type_id:
                if class_by_controltype is not None or class_by_legacy is not None:
                    raise Exception('pikuli.UIElement [INTERNAL]: more than one class are suitable for UI-element \'%s\':' % UIElement(winuielem).Name +
                                    '\n\tclass_by_controltype = \'%s\'\n\tclass_by_legacy = \'%s\'\n\tclass_ = \'%s\'' % (class_by_controltype, class_by_legacy, class_))
                class_by_controltype = class_

        elif class_control_type == 'Custom' and winuielem_ControlType == UIA.UIA_automation_control_type_identifiers_mapping['Custom']:
            if class_legacy_accessible_role is None:
                raise Exception('pikuli.UIElement [INTERNAL]: CONTROL_TYPE = \'Custom\', but LEGACYACC_ROLE is not setted for <class %s>. Processing controll \'%s\'' % (class_, UIElement(winuielem).Name))
            else:
                class_legacy_accessible_role_id = ROLE_SYSTEM.get(class_legacy_accessible_role, None)
                if class_legacy_accessible_role_id is None:
                    raise Exception('pikuli.UIElement [INTERNAL]: \'class_legacy_accessible_role_id\' is None for UIElement Control \'%s\'.' % UIElement(winuielem).Name)
                if winuielem_CurrentRole == class_legacy_accessible_role_id:
                    if class_by_controltype is not None or class_by_legacy is not None:
                        raise Exception('pikuli.UIElement [INTERNAL]: more than one class are suitable for UI-element \'%s\':' % UIElement(winuielem).Name +
                                        '\n\tclass_by_controltype = \'%s\'\n\tclass_by_legacy = \'%s\'\n\tclass_ = \'%s\'' % (class_by_controltype, class_by_legacy, class_))
                    class_by_legacy = class_

    if class_by_controltype is not None:
        return globals()[class_by_controltype](winuielem)
    elif class_by_legacy is not None:
        return globals()[class_by_legacy](winuielem)
    else:
        return UIElement(winuielem)



class UIElement(object):
    '''
    Доступные поля:
        pid            --  PID процесса, которому принадлежит окно
        hwnd           --  win32 указатель на искомое окно
        name()         --  заголовок искомого окна (для кнопок/чек-боксов/т.п. -- это их надписи)
        proc_name      --  имя процесса (exe-файла), которому принадлежит окно
    '''

    def __init__(self, pointer2elem, derived_self=None, required_patterns=[]):  #, timeout=10):
        '''
        Аргументы:
            pointer2elem       --  Некий указатель на UI-элемент (см. ниже).
            derived_self       --  Если пришли сюда из конструктора дочернего класса, то здесь хранится self создаваемого объета (можно узнать тип дочернего класса)
            required_patterns  --  Список занвание паттернов, которые потьребуются для работы (зависит от выбранного дочернего класса, экземпляр которого создается)
            #timeout            --  Если происходит какая-то ошибка, что пробуем повторить ошибочную процедуру, пока не превысим timeout. Пока ошибка может быть только в происке процесса по PID.

        Возможные значения аргумента pointer2elem:
            a) pointer2elem == hwnd искомого элемента GUI. В часности ноль -- это указатель корневой UIA-элемент ("рабочий стол").
            b) pointer2elem -- это уже интерфейс к искомому элементу GUI (указатель на обект типа IUIAutomationElement или экземпляр настоящего класса UIElement)

        Возвращение методами этого класса объектов UI-элементов (реализовано в функции _create_instance_of_suitable_class):
             1. Если self._winuiaelem позволяет получить ControlType, ищется подходящий класс (дочерний для _uielement_Control) с сооветствующим занчением атрибута CONTROL_TYPE.
             2. Если self._winuiaelem = 'Custom', то запрашивается LegacyIAccessible.Role и ищется класс с сответствующим значением LEGACYACC_ROLE.
             3. Если по какой-то причние пункты 1 и 2 выше не позволили подобрать класс, то испульзуется родительский UIElement.
             4. Если нашлось несколько подходящих классов, то генерируется исключение.
        '''
        self.default_find_timeout = DEFAULT_FIND_TIMEOUT
        self._reg = None

        if pointer2elem == 0:
            # Коренвой элемент.
            self._winuiaelem = UIA.IUIAutomation_object.GetRootElement()
            self._from_hwnd  = True
            self.pid         = None
            self.hwnd        = 0
            self.proc_name   = None

        else:
            if isinstance(pointer2elem, UIA.type_IUIAutomationElement):
                self._winuiaelem = pointer2elem
                self._from_hwnd = False
            elif isinstance(pointer2elem, UIElement):
                self._winuiaelem = pointer2elem._winuiaelem
                self._from_hwnd = False
            elif isinstance(pointer2elem, int) or isinstance(pointer2elem, long):
                self._winuiaelem = UIA.IUIAutomation_object.ElementFromHandle(pointer2elem)
                self._from_hwnd = True
            else:
                raise Exception('pikuli.UIElement: can not construct UIElement')

            self.pid   = self._winuiaelem.CurrentProcessId
            self.hwnd  = self._winuiaelem.CurrentNativeWindowHandle
            self.proc_name = None
            for proc in psutil.process_iter():
                try:
                    _processes = proc.as_dict(attrs=['pid', 'name'])
                    if proc.pid == self._winuiaelem.CurrentProcessId:
                        self.proc_name = proc.name()
                        break
                except psutil.NoSuchProcess:
                    pass
            if self.proc_name is None:
                raise Exception('pikuli.ui_element.UIElement.__init__(): self.proc_name is None -- Cannot find process with self.pid = %s and self.hwnd = %s\n\trepr(self) = %s\n\tstr(self):%s\n\tprocesses:\n%s'
                                % (str(self.pid), str(self.hwnd), repr(self), str(self), str(_processes)))

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

    def __str__(self):
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

    def __repr__(self):
        name = repr(self.Name)  #.encode('utf-8')
        if type(self).__name__ in CONTROLS_CLASSES:
            return u'<%s \'%s\',\'%s\'>' % (type(self).__name__, name, getattr(self, 'AutomationId', ''))
        control_type_id = self.get_property('ControlType')
        legacy_role_id  = self.get_pattern('LegacyIAccessiblePattern').CurrentRole
        return u'<%s %s,%s,\'%s\',\'%s\'>' % (type(self).__name__, UIA.UIA_automation_control_type_identifiers_mapping_rev.get(control_type_id, control_type_id), ROLE_SYSTEM_rev.get(legacy_role_id, legacy_role_id), name, getattr(self, 'AutomationId', ''))

    def get_property(self, name):
        if not hasattr(self, '_winuiaelem'):
            raise Exception('pikuli.UIElement.find [INTERNAL]: not hasattr(self, \'_winuiaelem\')')
        return UIA.get_property_by_id(self._winuiaelem, name)

    def get_pattern(self, name):
        if not hasattr(self, '_winuiaelem'):
            raise Exception('pikuli.UIElement.find [INTERNAL]: not hasattr(self, \'_winuiaelem\')')
        try:
            pattern = Pattern(self._winuiaelem, name)
        except DriverException:
            pattern = None
        return pattern

    def _test4readiness(self):
        ''' TODO: По идеи, надо сделать некую проврку, что класс создан правильно и готов к использованию.
        if self.is_empty():
            raise Exception('pikuli.UIElement.find: this is an empty class. Initialise it first.')'''
        return True


    def find_all(self, **kwargs):
        kwargs['find_first_only'] = False
        return self.find(**kwargs)


    #def find(self, _criteria, find_first_only=True, max_descend_level=None, exact_level=None, exception_on_find_fail=None):
    #def find(self, AutomationId=True, ClassName=True, Name=True, ControlType=True, ProcessId=True,
    #         find_first_only=True, max_descend_level=None, exact_level=None, exception_on_find_fail=None):
    def find(self, **kwargs):
        '''
        Поиск дочернего окна-объекта любого уровня вложенности. Под окном пнимается любой WinForms-элемент любого класса.

        В **kwargs можно передавать следующие поля, использующиеся для сравнения с одноименноыми UIA-свойствами элементов интерфейса:
            AutomationId     --  Неки текстовый ID, который, видимо, может назанчаться при создании тестируемой программы.
            ClassName        --  Имя класса. К примеру, "WindowsForms10.Window.8.app.0.1e929c1_r9_ad1".
            Name             --  Имя (title) искомого элемента UI.
            ControlType      --  Тип контрола. Строковое название из структуры UIA_automation_control_type_identifiers_mapping / списка UIA_automation_control_type_identifiers.
                                 (см. также "Control Type Identifiers", https://msdn.microsoft.com/en-us/library/windows/desktop/ee671198(v=vs.85).aspx)
            ProcessId        --  Для UAI это число (PID). Дополним возможность указания строки -- имени исполняемого файла, по которому предварительно будем определять PID.

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

        Возвращает:
            объект типа Region.
        '''
        self._test4readiness()
        # p2c(kwargs)

        # Обработка воходных аргументов:
        find_first_only        = kwargs.pop('find_first_only', True)
        max_descend_level      = kwargs.pop('max_descend_level', None)
        exact_level            = kwargs.pop('exact_level', None)
        exception_on_find_fail = kwargs.pop('exception_on_find_fail', None)
        timeout                = kwargs.pop('timeout', None)

        if timeout is None:
            timeout = self.default_find_timeout
        if exception_on_find_fail is None:
            exception_on_find_fail = find_first_only

        if max_descend_level is not None and exact_level is not None:
            raise Exception('pikuli.UIElement.find: max_descend_level is not None and exact_level is not None')
        if max_descend_level is not None and max_descend_level < 1:
            raise Exception('pikuli.UIElement.find: max_descend_level is not None and max_descend_level < 1')

        criteria = {}
        not_none_criteria = {}
        for key in ['AutomationId', 'ClassName', 'Name']:
            val = kwargs.pop(key, None)
            if val is not None:
                not_none_criteria[key] = val
                if isinstance(val, unicode):
                    val = str(val)
                if isinstance(val, list) and not reduce(lambda r, t: r and isinstance(t, str), val, True) or \
                   not isinstance(val, list) and not (hasattr(val, 'match') or isinstance(val, str)):
                        raise Exception('pikuli.UIElement.find: wrong kwargs[\'%s\'] = \'%s\'' % (str(key), str(val)))
            criteria[key] = val

        val = kwargs.pop('ControlType', None)
        if val is not None:
            not_none_criteria['ControlType'] = val
            if val not in UIA.UIA_automation_control_type_identifiers_mapping:
                raise Exception('pikuli.UIElement.find: ControlType is not None (\'%s\'), but not from UIA.UIA_automation_control_type_identifiers_mapping' % val)
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
                raise Exception('pikuli.ui_element.UIElement.find(): can not find process by its name; ProcessId = \'%s\'' % str(val))
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
            raise Exception('pikuli.UIElement.find: kwargs has unknown fields %s\n\tkwargs = %s' % (kwargs.keys(), str(kwargs)))

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

            for key in ['AutomationId', 'ClassName', 'Name']:
                if criteria[key] is None:
                    continue
                try:
                    uielem_val = winuiaelem.GetCurrentPropertyValue(UIA.UIA_automation_element_property_identifers_mapping[key])
                except Exception as ex:
                    # p2c(str(self), repr(self))
                    raise ex
                if isinstance(criteria[key], list):
                    for substr in criteria[key]:
                        if not (substr in uielem_val):
                            return False
                elif isinstance(criteria[key], str):
                    if not (uielem_val == criteria[key]):
                        return False
                else:  # re.complile
                    if not (criteria[key].match(uielem_val) is not None):
                        return False

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

                    """try:
                        p2c(repr(UIElement(elem)))
                    except:
                        p2c('-- some exception --')"""

                (current_level_todo_arr, next_level_todo_arr, level) = _goto_next_level()

            return found_winuiaelem_arr


        def _descendants_exact_level(walker, winuiaelem, level=0):
            if level < exact_level:  # exact_level > 0; level от вызова к вызову +1 (растет от 0).
                found_winuiaelem_arr = []
                child_winuiaelem = walker.GetFirstChildElement(winuiaelem)
                while child_winuiaelem:
                    # print '*', found_winuiaelem_arr, _descendants_exact_level(walker, child_winuiaelem, level+1)
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
                raise Exception('pikuli.UIElement.find: exact_level > 0 && level > exact_level\n\texact_level = %s\n\tlevel = %s' %
                                tuple(map(str, [exact_level, level])))
        # - subroutines: end -

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
                            raise FindFailed('pikuli.UIElement.find: no one elements was found\n\tself = %s\n\tkwargs = %s\n\tcriteria = %s\n\ttimeout = %s'
                                             % (repr(self), str(kwargs), str__criteria, str(timeout)))
                        p2c( 'Pikuli.ui_element.UIElement.find: %s has been found: None' % str__not_none_criteria)
                        return None
                    t0 = datetime.datetime.today()
                else:
                    found_elem = _create_instance_of_suitable_class(ex.winuiaelem)
                    p2c( 'Pikuli.ui_element.UIElement.find: %s has been found: %s' % (str__not_none_criteria, repr(found_elem)))
                    return found_elem

            except _ctypes.COMError as ex:
                if ex.args[0] == COR_E_TIMEOUT or ex.args[0] == COR_E_SUBSCRIBERS_FAILED:
                    p2c('Cath %s exception: %s. Checking custom timeout...' % (NAMES_of_COR_E[ex.args[0] ], str(ex)))
                    if (datetime.datetime.today()-t0).total_seconds() >= timeout:
                        raise FindFailed('find(...): Timeout while looking for UIA element:\n\tself = %s\n\tkwargs = %s' % (repr(self), str(kwargs)))
                    t0 = datetime.datetime.today()
                else:
                    tb_text = ''.join(traceback.format_list(traceback.extract_tb(sys.exc_info()[2])[1:]))
                    full_text = 'Traceback for error point:\n' + tb_text.rstrip() + '\nError message:\n  ' + type(ex).__name__ + ': ' + str(ex)
                    p2c(full_text)
                    raise ex

            else:
                # Тут, если ищем один элемент и все никак его не найдем или ищем много элементов:
                if not find_first_only or (find_first_only and (datetime.datetime.today()-t0).total_seconds() >= timeout):
                    break
                t0 = datetime.datetime.today()

        # В норме мы тут если ищем все совпадения (если ищем только первое, то должно было произойти и перехватиться исключение FirstFoundEx).
        if find_first_only:
            raise('pikuli.UIElement.find [INTERNAL]: Strange! We should not be here: ' + str(getframeinfo(currentframe())))
        if len(found_winuiaelem_arr) == 0:
            if exception_on_find_fail:
                raise FindFailed('pikuli.UIElement.find: no one elements was found\n\tself = %s\n\tkwargs = %s\n\tcriteria = %s' % (repr(self), str(kwargs), str__criteria))
            found_elem = []
            p2c( 'Pikuli.ui_element.UIElement.find: %s has been found: []' % str__not_none_criteria)
        else:
            found_elem = map(_create_instance_of_suitable_class, found_winuiaelem_arr)
            p2c('Pikuli.ui_element.UIElement.find: %s has been found: %s' % (str__not_none_criteria, repr(found_elem)))
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
            self._reg = Region.Region(xc, yc, wc, hc, winctrl=self, title=self.Name)
        else:
            rect = self._winuiaelem.GetCurrentPropertyValue(UIA.UIA_automation_element_property_identifers_mapping['BoundingRectangle'])
            try:
                rect = map(int, rect)
            except ValueError:
                raise FailExit('pikuli.UIElemen.reg(...): can not round numbers in rect = %s' % str(rect))
            self._reg = Region.Region(*rect, winctrl=self, title=self.Name)

        return self._reg


    def wait_prop_chage(self, prop_name, timeout=None):
        ''' TODO: events
        IUIAutomation_object.AddFocusChangedEventHandler

        from inspect import currentframe, getframeinfo, getargspec
        import comtypes
        import ctypes

        print comtypes.POINTER(comtypes.c_int)()

        import sys
        sys.path.append(r'Z:\python-shared-modules')
        from pikuli.ui_element import *
        from pikuli.UIA import *

        #print hasattr(UIA_wrapper, 'IUnknown')
        #print hasattr(UIA_wrapper, 'IUIAutomationPropertyChangedEventHandler')
        print '1>', filter(lambda f: 'uui' in f, dir(UIA_wrapper))
        print '2>', filter(lambda f: 'uui' in f, dir(IUIAutomation_object))
        print UIA_wrapper.IUIAutomation
        print UIA_wrapper.CUIAutomation
        print comtypes.POINTER(UIA_wrapper.IUIAutomationPropertyChangedEventHandler)()._iid_
        print comtypes.POINTER(UIA_wrapper.IUIAutomationPropertyChangedEventHandler)()

        """CreateObject(
            comtypes.POINTER(UIA_wrapper.IUIAutomationPropertyChangedEventHandler)()._iid_,
            None,
            None,
            UIA_wrapper.IUIAutomationPropertyChangedEventHandler
        )"""

        but = Button(0x500C6)
        print IUIAutomation_object.AddPropertyChangedEventHandlerNativeArray(
            but._winuiaelem,
            UIA_wrapper.TreeScope_Element,
            None,
            comtypes.POINTER(UIA_wrapper.IUIAutomationPropertyChangedEventHandler)(),
            [30005],
            1
        )
        '''
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


class _uielement_Control(UIElement):

    def __init__(self, *args, **kwargs):
        if hasattr(self, 'REQUIRED_PATTERNS'):
            required_patterns = self.REQUIRED_PATTERNS
        else:
            required_patterns = []
        super(_uielement_Control, self).__init__(*args, **kwargs)
        for pattern in ['LegacyIAccessiblePattern'] + required_patterns:
            if self.get_property('Is'+pattern+'Available') is None:
                raise Exception('pikuli.UIElement: UIElement Control \'%s\' does not support \'%s\'' % (self.Name, pattern))

    def is_unavailable(self):
        return bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['UNAVAILABLE'])

    def is_available(self):
        return (not self.is_unavailable())

    def is_focused(self):
        return bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['FOCUSED'])

    def bring_to_front(self):
        self._test4readiness()
        return hwnd_element.HWNDElement(self).bring_to_front()


class _ValuePattern_methods(UIElement):

    def get_value(self):
        return self.get_pattern('ValuePattern').CurrentValue

    def set_value(self, text):
        self.get_pattern('ValuePattern').SetValue(str(text))

    def is_readoly(self):
        return bool(self.get_pattern('ValuePattern').CurrentIsReadOnly)



"""class MainWindow(_uielement_Control):

    def __init__(self, *args, **kwargs):
        '''
            kwargs:
                proc_img_name  --  Имя исполняемого файла.
                in_title       --  Список строк, каждая их которых должна быть подстрокой заголовка искомого окна.
                title_regexp   --  Использовать ли регулярные выражения (True|False). Если in_title -- список, то применяется к каждому его эелементу.

            Если задано несколько коритерием поиска, то применяется условие AND.
        '''
        proc_img_name = kwargs.get('proc_img_name', None)
        in_title      = kwargs.get('in_title', None)
        title_regexp  = kwargs.get('title_regexp', False)

        if (in_title is not None) and (not isinstance(in_title, list)):
            in_title = [in_title]
        if title_regexp:
            raise Exception('pikuli.uielements.MainWindow: TODO -- title_regexp is unsupported yet!')

        # Поиск всех дочерних для корня (рабочего стола) элементов первогоуровня, иными словами -- главных окон:
        root      = UIA.IUIAutomation_object.GetRootElement()
        scope     = UIA.UIA_wrapper.TreeScope_Children
        condition = UIA.IUIAutomation_object.CreateTrueCondition()
        winuiaelem_arr = root.FindAll(scope, condition)  # Вернет объект типа "IUIAutomationElementArray"

        is_ = []
        # Проверка на имя процесса:
        if proc_img_name is not None:
            for i in range(winuiaelem_arr.Length):
                for proc in psutil.process_iter():
                    if (proc.pid == winuiaelem_arr.GetElement(i).CurrentProcessId) and (proc_img_name == proc.name()):
                        is_.append(i)

        # Проверка на заголовок окна:
        if in_title is not None:
            for i in range(winuiaelem_arr.Length):
                name = winuiaelem_arr.GetElement(i).CurrentName
                do_add = True
                for substr in in_title:
                    if substr not in name:
                        do_add = False
                if do_add:
                    is_.append(i)

        # Оценка результатов поиска:
        if len(is_) == 0:
            raise FindFailed('pikuli.uielements.MainWindow: no one window was found: proc_img_name = %s, in_title = %s' % tuple(map(str, [proc_img_name, in_title])))
        if len(is_) != 1:
            raise FindFailed('pikuli.uielements.MainWindow: multiple windows was found: proc_img_name = %s, in_title = %s' % tuple(map(str, [proc_img_name, in_title])))

        # Нашли, что хотели => вызываем конструктор класса-предка:
        super(MainWindow, self).__init__(winuiaelem_arr.GetElement(i))
        if self.get_property('ControlType') != UIA.UIA_automation_control_type_identifiers_mapping['Window']:
            raise Exception('pikuli.ui_element: UIElement Control \'%s\' is not a \'Window\' as desired.' % self.Name)"""


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

    def is_checked(self):
        return bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['CHECKED'])

    def is_unchecked(self):
        return not bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['CHECKED'])


class Edit(_uielement_Control, _ValuePattern_methods):

    CONTROL_TYPE = 'Edit'
    REQUIRED_PATTERNS = ['ValuePattern']


class Text(_uielement_Control, _ValuePattern_methods):

    CONTROL_TYPE = 'Text'
    REQUIRED_PATTERNS = ['ValuePattern']


class ComboBox(_uielement_Control, _ValuePattern_methods):

    CONTROL_TYPE = 'ComboBox'
    REQUIRED_PATTERNS = ['ValuePattern']

    def list_items(self):
        '''
            Если меню открыто, то вренут списко объектов, описывающих каждый пункт меню (теоретически, это может быть пустой список).
            Если меню закрыто, то вернет None.
        '''
        l = self.find(ControlType='List', exact_level=1, exception_on_find_fail=False)
        if l is None:
            return None
        return l.list_items()

    """def name_of_choosed(self):  --  есть метод _ValuePattern_methods.get_value()
        ''' Вернет тектсовую строку того пукта выпдающего меню, который выбран. '''
        return self.find(ControlType='Text', exact_level=1).get_value()"""

    def get_item_by_name(self, item_name):
        ''' Если список ракрыт, то вернут подходящий объект ListItem. Если объекта не нашлось в списке или список свернут, то будет исключение FindFailed. '''
        item_name = str(item_name)
        l = self.find(ControlType='List', exact_level=1, exception_on_find_fail=False)
        if l is None:
            raise FindFailed('List of ComboBox %s was not found. Is this list collapsed?' % repr(self))
        for i in l.find_all(ControlType='ListItem', exact_level=1):
            if i.Name == item_name:
                return i
        raise FindFailed('Item \'%s\' was not found in list of ComboBox %s.' % (item_name, repr(self)))



class Tree(_uielement_Control):

    CONTROL_TYPE = 'Tree'
    REQUIRED_PATTERNS = ['SelectionPattern']

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
            if not treeitem.has_subitems():
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
        items = self.find_all(exact_level=1)
        if len(items) == 0:
            return None
        return items

    def find_item(self, item_name, force_expand=False, timeout=None, exception_on_find_fail=True):
        '''
            item_name -- Cписок строк-названий эелементов дерева, пречисленных по их вложенности один в другой. Последняя строка в списке -- искомый элемент.
            force_expand -- разворачивать ли свернутые элементы на пути поиска искового.
        '''
        # p2c(item_name, force_expand)
        if not isinstance(item_name, list):
            raise Exception('pikuli.ui_element.Tree: not isinstance(item_name, list); item_name = %s' % str(item_name))
        if len(item_name) == 0:
            raise Exception('pikuli.ui_element.Tree: len(item_name) == 0')
        else:
            elem = self.find(Name=item_name[0], exact_level=1, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
            if elem is None:
                p2c('Pikuli.ui_element.Tree.find_item: %s has not been found. No exception -- returning None' % str(item_name))
                return None
            if len(item_name) == 1:
                found_elem = elem
            else:
                found_elem = elem.find_item(item_name[1:], force_expand, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
        p2c('Pikuli.ui_element.Tree.find_item: %s has been found by criteria \'%s\'' % (str(item_name), repr(found_elem)))
        return found_elem


class TreeItem(_uielement_Control):

    CONTROL_TYPE = 'TreeItem'
    REQUIRED_PATTERNS = ['SelectionItemPattern', 'ExpandCollapsePattern']

    def is_selected(self):
        return bool(self.get_pattern('SelectionItemPattern').CurrentIsSelected)

    def has_subitems(self):
        return not (self.get_pattern('ExpandCollapsePattern').CurrentExpandCollapseState == UIA.UIA_wrapper.ExpandCollapseState_LeafNode)

    def is_expanded(self):
        ''' Проверка, что развернут текущий узел (полностью, не частично). Без учета состояния дочерних узлов. Если нет дочерних, то функция вернет False. '''
        if not self.has_subitems():
            return False
        return (self.get_pattern('ExpandCollapsePattern').CurrentExpandCollapseState == UIA.UIA_wrapper.ExpandCollapseState_Expanded)

    def is_collapsed(self):
        ''' Проверка, что развернут текущий узел (полностью, не частично). Без учета состояния дочерних узлов. Если нет дочерних, то функция вернет True. '''
        if not self.has_subitems():
            return True
        return (self.get_pattern('ExpandCollapsePattern').CurrentExpandCollapseState == UIA.UIA_wrapper.ExpandCollapseState_Collapsed)

    def expand(self):
        if self.has_subitems() and not self.is_expanded():
            self.get_pattern('ExpandCollapsePattern').Expand()
        if not self.is_expanded():
            raise Exception('pikuli.ui_element: can not expand TreeItem \'%s\'' % self.Name)

    def collapse(self):
        if self.has_subitems() and not self.is_collapsed():
            self.get_pattern('ExpandCollapsePattern').Collapse()
        if not self.is_collapsed():
            raise Exception('pikuli.ui_element: can not collapse TreeItem \'%s\'' % self.Name)

    def list_current_subitems(self):
        ''' Вернут список дочерних узелков (1 уровень вложенности), если текущий узел развернут. Вернет [], если узел свернут полностью или частично. Вернет None, если нет дочерних узелков. '''
        if not self.has_subitems():
            return None
        if self.is_expanded():
            return self.find_all(exact_level=1)
        return []

    def find_item(self, item_name, force_expand=False, timeout=None, exception_on_find_fail=True):
        '''
            item_name -- Cписок строк-названий эелементов дерева, пречисленных по их вложенности один в другой. Последняя строка в списке -- искомый элемент.
            force_expand -- разворачивать ли свернутые элементы на пути поиска искового.
        '''
        if not isinstance(item_name, list):
            raise Exception('pikuli.ui_element.TreeItem: not isinstance(item_name, list); item_name = %s' % str(item_name))
        if len(item_name) == 0:
            raise Exception('pikuli.ui_element.TreeItem: len(item_name) == 0')
        if not self.is_expanded() and not force_expand:
            raise FindFailed('pikuli.ui_element.TreeItem: item \'%s\' was found, but it is not fully expanded. Try to set force_expand = True.\nSearch arguments:\n\titem_name = %s\n\tforce_expand = %s' % (self.Name, str(item_name), str(force_expand)))
        self.expand()
        elem = self.find(Name=item_name[0], exact_level=1, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
        if elem is None:
            p2c('Pikuli.ui_element.TreeItem.find_item: %s has not been found. No exception -- returning None' % str(item_name))
            return None
        if len(item_name) == 1:
            found_elem = elem
        else:
            found_elem = elem.find_item(item_name[1:], force_expand, timeout=timeout)
        p2c( 'Pikuli.ui_element.TreeItem.find_item: \'%s\' has been found: %s' % (str(item_name), repr(found_elem)))
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
        p2c( 'Pikuli.ui_element.ANPropGrid_Table.find_row: \'%s\' has been found: %s' % (str(row_name), repr(found_elem)))
        return found_elem


class ANPropGrid_Row(_uielement_Control):
    ''' Таблица настроек в AxxonNext ничего не поддерживает, кроме Legacy-паттерна.
    Каждая строка может группировать нижеидущие строки, но в UIA они "сестры", а не "родитель-потомки". Каждая строка можеть иметь или не иметь значения. '''

    CONTROL_TYPE = 'Custom'
    LEGACYACC_ROLE = 'ROW'  # Идентификатор из ROLE_SYSTEM

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

    def collase(self):
        if self.is_expanded():
            self.get_pattern('LegacyIAccessiblePattern').DoDefaultAction()
        if not self.is_collapsed():
            raise Exception('pikuli.ANPropGrid_Row.expand: string \'%s\' was not collapsed.' % self.Name)

    def get_value(self):
        return self.get_pattern('LegacyIAccessiblePattern').CurrentValue

    def set_value(self, text):
        self.get_pattern('LegacyIAccessiblePattern').SetValue(text)

    def type_text(self, text):
        ''' Кликнем мышкой по строке и введем новый текст без автоматического нажания ENTER'a.
        Клик мышкой в область с захардкоженным смещением, к сожалению -- иначе можно попасть в вертикальный разделитель колонок. '''
        self.reg().getTopLeft(30,1).click()
        type_text(text)

    def enter_text(self, text):
        ''' Кликнем мышкой по строке и введем новый текст c автоматическим нажания ENTER'a. Используется type_text(). '''
        self.type_text(str(text) + Key.ENTER)



class List(_uielement_Control):
    ''' Некий список из ListItem'ов. '''

    CONTROL_TYPE = 'List'

    def list_items(self):
        return self.find_all(ControlType='ListItem', exact_level=1)


class ListItem(_uielement_Control):
    ''' Элементы списка ListItem. '''

    CONTROL_TYPE = 'ListItem'




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




locals_keys = locals().keys()
CONTROLS_CLASSES = [i for i in locals_keys if isclass(locals()[i]) and issubclass(locals()[i], _uielement_Control) and locals()[i] != _uielement_Control and (hasattr(locals()[i], 'CONTROL_TYPE') or hasattr(locals()[i], 'ROLE_SYSTEM'))]
