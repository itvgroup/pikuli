# -*- coding: utf-8 -*-

from .uia_control import UIAControl


class Item(UIAControl):

    CONTROL_TYPE = 'DataItem'
    REQUIRED_PATTERNS = {}

    @property
    def value(self):
        return self.get_pattern('LegacyIAccessiblePattern').CurrentValue
