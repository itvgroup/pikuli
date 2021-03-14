# -*- coding: utf-8 -*-

import traceback

from pikuli import logger
from pikuli._helpers import NotImplemetedDummyBase, NotImplemetedDummyFactory
from .exceptions import AdapterException


try:
    from .adapter import Adapter as __Adapter
    assert not issubclass(__Adapter, NotImplemetedDummyBase), __Adapter.err_msg

    from .uia_element import UIAElement
    from .control_wrappers import Desktop

except Exception as ex:
    err_msg = traceback.format_exc()
    logger.exception(
        'NOTE: Cann\'t initialize class UIA API. A dummy will be used. Some features is not available.')
    (
        UIAElement,
        Desktop
    ) = NotImplemetedDummyFactory.make_classes(
        [
            'UIAElement',
            'Desktop'
        ],
        reason=err_msg)
