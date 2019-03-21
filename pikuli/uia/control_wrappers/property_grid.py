# -*- coding: utf-8 -*-

from pikuli import logger, FindFailed
from pikuli.uia.adapter import STATE_SYSTEM

from .uia_control import UIAControl
from .mixin import _LegacyIAccessiblePattern_value_methods, _Enter_Text_method


class ANPropGrid_Table(UIAControl):
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
            rows = [ANPropGrid_Row(e) for e in obj.find_all(Name=nested_name, exact_level=exact_level) if e.CONTROL_TYPE in ["Custom", "DataItem"]]
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


class ANPropGrid_Row(UIAControl, _LegacyIAccessiblePattern_value_methods, _Enter_Text_method):
    ''' Таблица настроек в AxxonNext ничего не поддерживает, кроме Legacy-паттерна.
    Каждая строка может группировать нижеидущие строки, но в UIA они "сестры", а не "родитель-потомки". Каждая строка можеть иметь или не иметь значения. '''

    CONTROL_TYPE = 'Custom'
    LEGACYACC_ROLE = 'ROW'  # Идентификатор из ROLE_SYSTEM
    _type_text_click = {'click_method': 'click', 'click_location': ('getTopLeft', (30,1), None), 'enter_text_clean_method': 'single_backspace'}

    def is_expandable(self):
        current_state = self.get_pattern('LegacyIAccessiblePattern').CurrentState
        return bool(current_state & STATE_SYSTEM['EXPANDED'] | current_state & STATE_SYSTEM['COLLAPSED'])

    def is_selectable(self):
        current_state = self.get_pattern('LegacyIAccessiblePattern').CurrentState
        return bool(current_state & STATE_SYSTEM['SELECTABLE'])

    def is_expanded(self):
        ''' Если трока не имеет дочерних, то функция вернет False. '''
        return (self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['EXPANDED'])

    def is_collapsed(self):
        ''' Если трока не имеет дочерних, то функция вернет False. '''
        return (self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['COLLAPSED'])

    """def list_current_subrows(self):
        ''' Вернут список дочерних строк (1 уровень вложенности), если текущая строка развернута. Вернет [], если строка свернута. Вернет None, если нет дочерних строк. '''

        if not self.is_expandable():
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
        return self.get_pattern('ValuePattern').CurrentValue


