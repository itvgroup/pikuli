# -*- coding: utf-8 -*-
from .mixin import _ValuePattern_methods
from .uia_control import UIAControl


class Image(UIAControl, _ValuePattern_methods):

    CONTROL_TYPE = 'Image'

