# -*- coding: utf-8 -*-
from .uia_control import UIAControl


class Button(UIAControl):

    CONTROL_TYPE = 'Button'

    def is_avaliable(self):
        return self.get_property("IsEnabled")

    def is_unavaliable(self):
        return not self.is_avaliable()
