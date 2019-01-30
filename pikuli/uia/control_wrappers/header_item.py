# -*- coding: utf-8 -*-
from pikuli.uia.control_wrappers.mixin import _LegacyIAccessiblePattern_value_methods

from .uia_control import UIAControl


class HeaderItem(UIAControl, _LegacyIAccessiblePattern_value_methods):

    CONTROL_TYPE = 'HeaderItem'
