# -*- coding: utf-8 -*-

from .adapter import Adapter
from .property_value_converter import PropertyValueConverter
from .oleacc_h import STATE_SYSTEM

from .platform_init import (
    AutomationElement,
    Condition,
    PatternFactory,
    TreeWalker,
)

PatternFactory.init(Adapter)

Enums = Adapter.Enums
