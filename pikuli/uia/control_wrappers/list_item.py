# -*- coding: utf-8 -*-
from pikuli.uia.adapter import Enums

from .uia_control import UIAControl


class ListItem(UIAControl):
    ''' Элементы списка ListItem. '''

    CONTROL_TYPE = 'ListItem'

    def select(self):
        self.get_pattern('SelectionItemPattern').Select()

    def is_selected(self):
        return bool(self.get_pattern('SelectionItemPattern').CurrentIsSelected)

    def is_checked(self):
        return bool(self.get_pattern('TogglePattern').CurrentToggleState)
