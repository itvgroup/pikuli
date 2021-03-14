# -*- coding: utf-8 -*-

from inspect import currentframe, getframeinfo, isclass
import time
import datetime
import traceback
import sys
import re
import logging
import json
import os

import psutil
from enum import Enum

# TODO:
if os.name == 'nt':
    import win32gui
    from .adapter.oleacc_h import ROLE_SYSTEM_rev
else:
    ROLE_SYSTEM_rev = {}

import pikuli.uia

from pikuli import wait_while
from pikuli.geom import Region
from pikuli._functions import verify_timeout_argument
from pikuli._exceptions import FindFailed, FailExit

from .exceptions import AdapterException, COMError
from .adapter import Adapter, PatternFactory, PropertyValueConverter, AutomationElement, Condition, Enums, TreeWalker
from .pattern import UiaPattern
from .settings import NEXT_SEARCH_ITER_DELAY, DEFAULT_FIND_TIMEOUT, DYNAMIC_FIND_TIMEOUT

# "A lot of HRESULT codes…" (https://blogs.msdn.microsoft.com/eldar/2007/04/03/a-lot-of-hresult-codes/)
COR_E_TIMEOUT = -2146233083  # -2146233083 =<математически>= -0x80131505;   0x80131505 =<в разрядной сетке>= (-2146233083 & 0xFFFFFFFF)
COR_E_SUBSCRIBERS_FAILED = -2147220991  # -2147220991 =<математически>= -0x80040201;
NAMES_of_COR_E = {
    COR_E_TIMEOUT: 'COR_E_TIMEOUT',
    COR_E_SUBSCRIBERS_FAILED: 'COR_E_SUBSCRIBERS_FAILED'
}

# CONSOLE_ERASE_LINE_SEQUENCE = '\033[F' + '\033[2K'

from pikuli import logger

'''
TODO:

    --- def check(self, method='click'):
        def click(self, method='click')
        Потенциально в качестве значения method могут быть click (подвести курсов мыши и кликнуть) или invoke (через UIA).

    --- обработка доступности LegacyIAccessiblePattern в основнмо классе UIAElement
'''

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

        Возвращение методами этого класса объектов UI-элементов (реализовано в методе `_make_suitable_uiaelement`:
             1. Если self._automation_element позволяет получить ControlType, ищется подходящий класс (дочерний для UIAControl) с сооветствующим занчением атрибута CONTROL_TYPE.
             2. Если self._automation_element = 'Custom', то запрашивается LegacyIAccessible.Role и ищется класс с сответствующим значением LEGACYACC_ROLE.
             3. Если по какой-то причние пункты 1 и 2 выше не позволили подобрать класс, то испульзуется родительский UIAElement.
             4. Если нашлось несколько подходящих классов, то генерируется исключение.
        '''
        self._find_timeout = verify_timeout_argument(find_timeout, err_msg='pikuli.UIAElement.__init__()')
        self._proc_name = None  # Кеш для proc_name

        if pointer2elem == 0:
            # Коренвой элемент.
            self._automation_element = AutomationElement.RootElement
            self._from_hwnd = True
            self._has_proc_name = False  # Объект будет возвращать None при запросе proc_name

        else:
            if Adapter.is_automation_element(pointer2elem):
                self._automation_element = pointer2elem
                self._from_hwnd = False
            elif isinstance(pointer2elem, UIAElement):
                self._automation_element = pointer2elem._automation_element
                self._from_hwnd = False
            elif isinstance(pointer2elem, int):
                self._automation_element = Adapter._IUIAutomation_obj.ElementFromHandle(pointer2elem)
                self._from_hwnd = True
            else:
                raise Exception('pikuli.UIAElement: can not construct UIAElement')

            self._has_proc_name = True  # Объект будет возвращать proc_name

    @property
    def pid(self):
        logger.warning("Depricated method: UIAElement.pid"'')
        #return self.get_property('ProcessId')
        return self.ProcessId

    @property
    def hwnd(self):
        logger.warning("Depricated method: UIAElement.hwnd"'')
        #return self.get_property('NativeWindowHandle')
        return self.NativeWindowHandle

    @property
    def proc_name(self):
        if self._has_proc_name and (self._proc_name is None):
            for proc in psutil.process_iter():
                try:
                    _processes = proc.as_dict(attrs=['pid', 'name'])
                    if proc.pid == self.ProcessId:
                        proc_name = proc.name()
                        break
                except psutil.NoSuchProcess:
                    pass
            if proc_name is None:
                raise Exception('pikuli.ui_element.UIAElement.__init__(): self.proc_name is None -- Cannot find process with self.pid = %s and self.hwnd = %s\n\trepr(self) = %s\n\tstr(self):%s\n\tprocesses:\n%s'
                                % (str(self.pid), str(self.hwnd), repr(self), str(self), str(_processes)))
        return proc_name

    def __getattr__(self, name, *args):
        '''
        we also support direct use name to get object
        '''
        attr = self.get_property(name)
        if attr is not None:
            if name == 'ControlType':
                return Adapter.get_control_type_name(attr)
            return attr

        attr = self.get_pattern(name)
        if attr is not None:
            return attr

        if name in Adapter.known_element_property_names:
            return None
    
        raise AttributeError("Attribute {!r} not exist in {}".format(name, type(self)))

    def _short_info(self):
        hwnd = getattr(self, 'NativeWindowHandle', '')
        if hwnd:
            try:
                hwnd = hex(int(hwnd)).upper().replace('X', 'x')
            except:
                pass
            hwnd = ', ' + str(hwnd)

        name = repr(getattr(self, 'Name', '<no Name>'))  #.encode('utf-8')
        if pikuli.uia.control_wrappers.RegisteredControlClasses.is_class_registred(self):
            return u'<%s \'%s\',\'%s\'%s>' % (
                type(self).__name__,
                name,
                getattr(self, 'AutomationId', ''),
                hwnd)

        try:
            legacy_patten = self.get_pattern('LegacyIAccessiblePattern')
            legacy_role_id = getattr(legacy_patten, 'CurrentRole', None)  # LegacyIAccessiblePattern will be None in case of CustomControl.
        except:
            legacy_role_id = None

        control_type_id = self.get_property('ControlType')
        try:
            control_type = Adapter.get_control_type_name(control_type_id)
        except:
            control_type = '<wrong ControlType {}>'.format(control_type_id)
        return u'<%s %s, %s,\'%s\',\'%s\',\'%s\',%s>' % (
            type(self).__name__,
            control_type,
            ROLE_SYSTEM_rev.get(legacy_role_id, legacy_role_id) if ROLE_SYSTEM_rev else "<no ROLE_SYSTEM_rev>",
            name,
            getattr(self, 'AutomationId', ''),
            getattr(self, 'LocalizedControlType', ''),
            hwnd)

    def _long_info(self):
        docstring = ""
        # generate UIA automation element properties
        docstring += "+ UIA automation element properties: +\n"
        for identifier in Adapter.get_api_property_names():
            value = self.get_property(identifier)
            if value is not None:
                docstring += "  %-24s:\t%s\n" % (identifier, repr(value))

        """docstring += "\n"
        # generate UIA control pattern availability properties (from "Control Pattern Identifiers")
        docstring += "+ UIA control pattern availability properties: +\n"
        for identifier in sorted(UIA.UIA_control_pattern_availability_property_identifiers_mapping):
            value = self.get_property(identifier)
            if value is not None:
                docstring += "  %-35s:\t%s\n" % (identifier, repr(value))"""

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
        id_ = Adapter.try_get_property_id(name)
        if id_ is None:
            return None
        property_value = self._automation_element.GetCurrentPropertyValue(id_)
        #if property_value is None:
        #    raise Exception("Property {} is not supported by this UIAElment".format(property_name))
        return PropertyValueConverter.convert(name, property_value)

    def get_pattern(self, pattern_name):
        try:
            pattern = UiaPattern(self._automation_element, pattern_name)
        except AdapterException:
            pattern = None
        return pattern

    def get_supported_patterns(self):
        return Adapter.get_supported_patterns(self)

    def _test4readiness(self):
        ''' TODO: По идеи, надо сделать некую проврку, что класс создан правильно и готов к использованию.
        if self.is_empty():
            raise Exception('pikuli.UIAElement.find: this is an empty class. Initialise it first.')'''
        return True

    @classmethod
    def _make_suitable_uiaelement(self, automation_element, find_timeout=DEFAULT_FIND_TIMEOUT):
        tmp_uia_element = UIAElement(automation_element, find_timeout=find_timeout)

        cotrol_type = tmp_uia_element.ControlType
        class_by_controltype = pikuli.uia.control_wrappers.RegisteredControlClasses.get_class_by_control_type(cotrol_type)

        # .Net (not just Mono) doesn't support `LegacyIAccessiblePattern`.
        legacy_support = getattr(tmp_uia_element, 'IsLegacyIAccessiblePatternAvailable', None)

        if legacy_support:
            legacy_role = tmp_uia_element.LegacyIAccessiblePattern.CurrentRole
            class_by_legacyrole = pikuli.uia.control_wrappers.RegisteredControlClasses.try_get_by_legacy_role(legacy_role)
        else:
            class_by_legacyrole = None

        if class_by_controltype:
            return class_by_controltype(automation_element, find_timeout=find_timeout)
        elif class_by_legacyrole:
            return class_by_legacyrole(automation_element, find_timeout=find_timeout)
        else:
            return tmp_uia_element

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
                if isinstance(val, re.Pattern) or hasattr(val, 'match'):
                    pass
                elif isinstance(val, (list, tuple)):
                    val = list(map(str, val))
                else:
                    val = str(val)
            criteria[key] = val

        val = kwargs.pop('ControlType', None)
        if val is not None:
            not_none_criteria['ControlType'] = val
            val = Adapter.get_control_type_id(val)
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
            def __init__(self, automation_element):
                self.automation_element = automation_element
                super(Exception, self).__init__()

        def _is_automation_element_suitable(automation_element):
            if criteria['ProcessId'] is not None and criteria['ProcessId'] != automation_element.CurrentProcessId:
                return False

            if (criteria['ControlType'] is not None and
                criteria['ControlType'] != automation_element.GetCurrentPropertyValue(Adapter.try_get_property_id('ControlType'))):
                return False

            for key in ['AutomationId', 'ClassName', 'Name', 'LocalizedControlType']:
                if criteria[key] is None:
                    continue

                try:
                    prop_id = Adapter.try_get_property_id(key)
                    uielem_val = automation_element.GetCurrentPropertyValue(prop_id)
                    if uielem_val is None:
                        return False
                except Exception as ex:
                    raise ex

                if isinstance(criteria[key], list):
                    for substr in criteria[key]:
                        if uielem_val is None or not (substr in uielem_val):
                            return False
                elif isinstance(criteria[key], str):
                    if not (uielem_val == criteria[key]):
                        return False
                elif isinstance(criteria[key], re.Pattern) or hasattr(criteria[key], 'match'):  # re.complile
                    if not (criteria[key].match(uielem_val) is not None):
                        return False
                else:
                    raise Exception('%s: unsupported value \"%s\" of key \'%s\'' % (_func_name, str(criteria[key]), str(key)))

            return True

        def _search_with_method(start_automation_element, method_f):
            found_automation_element_arr_local = []
            next_automation_element = method_f(start_automation_element)
            while next_automation_element:
                if _is_automation_element_suitable(next_automation_element):
                    if find_first_only:
                        raise FirstFoundEx(next_automation_element)
                    found_automation_element_arr_local.append(next_automation_element)
                next_automation_element = method_f(next_automation_element)
            return found_automation_element_arr_local


        '''
        # Поиск по веткам элементов:
        def _descendants_range_level(walker, automation_element, level=0):
            found_automation_element_arr = []

            if max_descend_level is None or level < max_descend_level:  # max_descend_level > 0; level от вызова к вызову +1 (растет от 0).
                child_automation_element = walker.GetFirstChild(automation_element)
                while child_automation_element:
                    if _is_automation_element_suitable(child_automation_element):
                        if find_first_only:
                            raise FirstFoundEx(child_automation_element)
                        found_automation_element_arr += [child_automation_element]

                    if max_descend_level is None or level < max_descend_level - 1:
                        found_automation_element_arr += _descendants_range_level(walker, child_automation_element, level+1)

                    child_automation_element = walker.GetNextSibling(child_automation_element)

            return found_automation_element_arr'''

        # Поиск по слоям вложенности:
        def _descendants_range_level(walker, automation_element):
            found_automation_element_arr   = []
            current_level_todo_arr = []
            next_level_todo_arr    = []
            level                  = 0

            def _add_to_next_level_todo(root_elem):
                if max_descend_level is None or level < max_descend_level:
                    try:
                        elem = walker.GetFirstChild(root_elem)
                    except Exception as ex:
                        raise FindFailed(ex)
                    while elem:
                        next_level_todo_arr.append( elem )
                        elem = walker.GetNextSibling(elem)

            def _goto_next_level():
                return (next_level_todo_arr, [], level+1)

            _add_to_next_level_todo(automation_element)
            (current_level_todo_arr, next_level_todo_arr, level) = _goto_next_level()

            while len(current_level_todo_arr) != 0:

                while len(current_level_todo_arr) != 0:
                    elem = current_level_todo_arr.pop(0)
                    if _is_automation_element_suitable(elem):
                        if find_first_only:
                            raise FirstFoundEx(elem)
                        found_automation_element_arr.append( elem )
                    _add_to_next_level_todo(elem)


                (current_level_todo_arr, next_level_todo_arr, level) = _goto_next_level()

            return found_automation_element_arr


        def _descendants_exact_level(walker, automation_element, level=0):
            if level < exact_level:  # exact_level > 0; level от вызова к вызову +1 (растет от 0).
                found_automation_element_arr = []
                child_automation_element = walker.GetFirstChild(automation_element)
                while child_automation_element:
                    found_automation_element_arr += _descendants_exact_level(walker, child_automation_element, level+1)
                    child_automation_element = walker.GetNextSibling(child_automation_element)
                return found_automation_element_arr

            elif level == exact_level:
                if _is_automation_element_suitable(automation_element):
                    if find_first_only:
                        raise FirstFoundEx(automation_element)
                    return [automation_element]
                return []

            else:  # exact_level > 0 && level > exact_level
                raise Exception('%s: exact_level > 0 && level > exact_level\n\texact_level = %s\n\tlevel = %s' %
                                tuple(map(str, [_func_name, exact_level, level])))
        # - subroutines: end -
        txt_search_timeout        = 'searching with timeout = %s (call/class/module: %s/%s/%s) ...' % (str(timeout), str(_timeout), str(self._find_timeout), str(DEFAULT_FIND_TIMEOUT))
        txt_pikuli_search_pattern = '%s: by criteria %s %%s' % (_func_name, str__not_none_criteria)
        logger.debug(txt_pikuli_search_pattern % txt_search_timeout)

        walker = TreeWalker(Condition.TrueCondition)
        t0 = datetime.datetime.today()
        while True:
            try:
                # Исключение FirstFoundEx используется как goto.
                if exact_level is not None:
                    # Обработаем варианты поиска предков:
                    if exact_level < 0:
                        automation_element = self._automation_element
                        for level in range(-exact_level):
                            automation_element = walker.GetParent(automation_element)
                        if find_first_only:
                            # TODO: можом получить структуру automation_element, указывающую на ptr=0, если нет родителя заданного уровня. Надо обработать, но не знаю пока как.
                            raise FirstFoundEx(automation_element)
                        found_automation_element_arr = [automation_element]

                    # Обработаем варианты поиска братьев-сестер:
                    elif exact_level == 0:
                        found_automation_element_arr = _search_with_method(self._automation_element, walker.GetNextSibling)
                        if find_first_only and len(found_automation_element_arr) != 0:
                            raise FirstFoundEx(found_automation_element_arr[0])
                        found_automation_element_arr += _search_with_method(self._automation_element, walker.GetPreviousSibling)
                        if find_first_only:
                            if len(found_automation_element_arr) == 0:
                                raise FirstFoundEx(None)
                            raise FirstFoundEx(found_automation_element_arr[0])

                    # Обработаем вариант поиска потомков (descendants).
                    else:
                        # Поиск по веткам элементов:
                        found_automation_element_arr = _descendants_exact_level(walker, self._automation_element)
                        if find_first_only:
                            if len(found_automation_element_arr) == 0:
                                raise FirstFoundEx(None)
                            raise FirstFoundEx(found_automation_element_arr[0])

                else:
                    # Теперь обработаем вариант поиска потомков в диапазоне возможных вложенностей.
                    # Будем искать по слоям вложенности элементов, а не по веткам. Это немного сложнее сделать, но должно быть эффективнее.
                    found_automation_element_arr = _descendants_range_level(walker, self._automation_element)

                if find_first_only and len(found_automation_element_arr) == 0:
                    raise FirstFoundEx(None)

            except FirstFoundEx as ex:
                if ex.automation_element is None:
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
                    found_elem = UIAElement._make_suitable_uiaelement(ex.automation_element, find_timeout=self._find_timeout)
                    # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
                    logger.debug(txt_pikuli_search_pattern % ('has been found: %s (%s)' % (repr(found_elem), str(timeout))))
                    return found_elem

            except COMError as ex:
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
        if len(found_automation_element_arr) == 0:
            if exception_on_find_fail:
                raise FindFailed('%s: no one elements was found\n\tself = %s\n\tkwargs = %s\n\tcriteria = %s' % (_func_name, repr(self), str(kwargs), str__criteria))
            found_elem = []
            # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
            logger.debug(txt_pikuli_search_pattern % ('there has been found no one UI-elem (%s)' % (str(timeout))))
        else:
            found_elem = [UIAElement._make_suitable_uiaelement(ae, find_timeout=self._find_timeout) for ae in found_automation_element_arr]

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
            reg = Region(xc, yc, wc, hc, winctrl=self, title=self.Name, find_timeout=self._find_timeout)
        else:
            rect = map(int, self.get_bounding_rectangle())

            try:
                name = self.Name
            except Exception:
                logger.info("{} has not attribute Name. Name=''".format(self))
                name = ""

            reg = Region(*rect, winctrl=self, title=name, find_timeout=self._find_timeout)

        return reg

    @property
    def region(self):
        return self.reg()

    def wait_prop_chage(self, prop_name, timeout=None):
        prop_id = Adapter.try_get_property_id(prop_name)
        if prop_id is None:
            raise FailExit('...')
        self.__wait_chages__prev_prop = self._automation_element.GetCurrentPropertyValue(prop_id)
        wait_while(lambda: self.__wait_chages__prev_prop == self._automation_element.GetCurrentPropertyValue(prop_id), timeout)

    def wait_prop_chage_to(self, prop_name, new_val, timeout=None):
        prop_id = Adapter.try_get_property_id(prop_name)
        if prop_id is None:
            raise FailExit('...')
        wait_while(lambda: new_val != self._automation_element.GetCurrentPropertyValue(prop_id), timeout)

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
