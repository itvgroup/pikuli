# -*- coding: utf-8 -*-

import traceback

from pikuli import logger
from pikuli._helpers import NotImplemetedDummyFactory

from .oleacc_h import STATE_SYSTEM

try:
    from .adapter import Adapter

    from .property_value_converter import PropertyValueConverter
    from .platform_init import (
        AutomationElement,
        Condition,
        PatternFactory,
        TreeWalker,
    )

    PatternFactory.init(Adapter)

    Enums = Adapter.Enums

except Exception as ex:
    err_msg = traceback.format_exc()
    #logger.exception(
    #    'NOTE: Cann\'t initialize class UIA API. A dummy will be used. Some features is not available.')
    (
        Adapter,
        PatternFactory,
        PropertyValueConverter,
        AutomationElement,
        Condition,
        TreeWalker,
        Enums
    ) = NotImplemetedDummyFactory.make_classes(
        [
            'Adapter',
            'PatternFactory',
            'PropertyValueConverter',
            'AutomationElement',
            'Condition',
            'TreeWalker',
            'Enums'
        ],
        reason=err_msg)
