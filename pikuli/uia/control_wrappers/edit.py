# -*- coding: utf-8 -*-

from .uia_control import UIAControl
from .mixin import _ValuePattern_methods, _Enter_Text_method

class Edit(UIAControl, _ValuePattern_methods, _Enter_Text_method):

    CONTROL_TYPE = 'Edit'
    REQUIRED_PATTERNS = {}
