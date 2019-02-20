# -*- coding: utf-8 -*-
from .uia_control import UIAControl
from .mixin import _ValuePattern_methods


class Header(UIAControl, _ValuePattern_methods):

    CONTROL_TYPE = 'Header'


