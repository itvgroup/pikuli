# -*- coding: utf-8 -*-

from .uia_control import UIAControl


class MenuItem(UIAControl):
    ''' Контекстное меню, к примеру. '''

    CONTROL_TYPE = 'MenuItem'
