# -*- coding: utf-8 -*-

from ..property_value_converter import PropertyValueConverterBase
from ..property_value_types import Rectangle


class PropertyValueConverter(PropertyValueConverterBase):

    @classmethod
    def convert_BoundingRectangle(cls, val):
        print val, dir(val)
        print val.Left, val.get_X()
        return Rectangle(val.Left, val.Top, val.Width, val.Height)
