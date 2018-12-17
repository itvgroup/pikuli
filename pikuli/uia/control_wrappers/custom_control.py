# -*- coding: utf-8 -*-

from ..uia_element import UIAElement


class CustomControl(UIAElement):
    """
    Cunstom (Graphic, for example) control. It does not support LegacyIAccessiblePattern, because this patternt
    adds to provider by Windows only for navire controls. But for all native ones.
    """

    CONTROL_TYPE = 'Custom'
