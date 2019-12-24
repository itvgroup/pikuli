# -*- coding: utf-8 -*-
from pikuli.uia.adapter import STATE_SYSTEM

from .mixin import _ValuePattern_methods, _Enter_Text_method
from .uia_control import UIAControl


class DataItem(UIAControl, _ValuePattern_methods, _Enter_Text_method):

    CONTROL_TYPE = 'DataItem'

    def select(self):
        self.SelectionItemPattern.Select()

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

    def collapse(self):
        if self.is_expanded():
            self.get_pattern('LegacyIAccessiblePattern').DoDefaultAction()

    """def type_text(self, text):
        ''' Кликнем мышкой по строке и введем новый текст без автоматического нажания ENTER'a.
        Клик мышкой в область с захардкоженным смещением, к сожалению -- иначе можно попасть в вертикальный разделитель колонок. '''
        self.region.getTopLeft(30,1).click()
        type_text(text)"""

    @property
    def value(self):
        return self.get_pattern('ValuePattern').CurrentValue

