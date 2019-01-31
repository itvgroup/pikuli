# -*- coding: utf-8 -*-
from pikuli.uia.adapter import STATE_SYSTEM

from .uia_control import UIAControl


class Button(UIAControl):

    CONTROL_TYPE = 'Button'

    def is_avaliable(self):
        return not bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['UNAVAILABLE'])

    def is_unavaliable(self):
        return bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['UNAVAILABLE'])
