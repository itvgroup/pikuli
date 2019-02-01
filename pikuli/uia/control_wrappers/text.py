# -*- coding: utf-8 -*-

from .uia_control import UIAControl
from .mixin import _ValuePattern_methods


class Text(UIAControl, _ValuePattern_methods):

    CONTROL_TYPE = 'Text'
    REQUIRED_PATTERNS = {}
