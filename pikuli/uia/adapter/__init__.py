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
    logger.exception(
        'NOTE: Cann\'t initialize class UIA API. A dummy will be used. Some features is not available.')
    Adapter = NotImplemetedDummyFactory.make_class(target_cls='Adapter', reason=err_msg)
    PatternFactory = NotImplemetedDummyFactory.make_class(target_cls='PatternFactory', reason=err_msg)
    PropertyValueConverter = NotImplemetedDummyFactory.make_class(target_cls='PropertyValueConverter', reason=err_msg)
    AutomationElement = NotImplemetedDummyFactory.make_class(target_cls='AutomationElement', reason=err_msg)
    Condition = NotImplemetedDummyFactory.make_class(target_cls='Condition', reason=err_msg)
    Enums = NotImplemetedDummyFactory.make_class(target_cls='Enums', reason=err_msg)
    TreeWalker = NotImplemetedDummyFactory.make_class(target_cls='TreeWalker', reason=err_msg)



