# -*- coding: utf-8 -*-

from .uia_control import UIAControl


class ListItem(UIAControl):
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
