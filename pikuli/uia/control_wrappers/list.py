# -*- coding: utf-8 -*-

from .uia_control import UIAControl


class List(UIAControl):
    ''' Некий список из ListItem'ов. '''

    CONTROL_TYPE = 'List'

    def list_items(self):
        return self.find_all(ControlType='ListItem', exact_level=1)
