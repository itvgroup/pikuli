# -*- coding: utf-8 -*-

from pikuli.uia.adapter.property_value_types import Rectangle


class DotNetPropertyValueConverter(object):

    @classmethod
    def convert_BoundingRectangle(cls, val):
        return Rectangle(val.Left, val.Top, val.Width, val.Height)
