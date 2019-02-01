# -*- coding: utf-8 -*-

from .uia_control import UIAControl


class Menu(UIAControl):
    ''' Контекстное меню, к примеру. Состоит из MenuItem. '''

    CONTROL_TYPE = 'Menu'

    def list_items(self):
        return self.find_all(ControlType='MenuItem', exact_level=1)

    def find_item(self, item_name, exception_on_find_fail=True):
        return self.find(Name=item_name, ControlType='MenuItem', exact_level=1, exception_on_find_fail=exception_on_find_fail)
