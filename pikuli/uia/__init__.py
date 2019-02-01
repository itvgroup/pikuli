# -*- coding: utf-8 -*-

import traceback

from pikuli import logger
from pikuli._helpers import NotImplemetedDummyFactory
from .exceptions import DriverException


try:
    from .uia_element import UIAElement
    from .control_wrappers import Desktop
except Exception as ex:
    err_msg = traceback.format_exc()
    logger.exception(ex,
        'NOTE: Cann\'t initialize class UIA API. A dummy will be used. Some features is not available.')
    UIAElement = NotImplemetedDummyFactory.make_class(target_cls='UIAElement', reason=err_msg)
    Desktop = NotImplemetedDummyFactory.make_class(target_cls='Desktop', reason=err_msg)
