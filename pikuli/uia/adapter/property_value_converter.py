# -*- coding: utf-8 -*-

import inspect

from .platform_init import OsPropertyValueConverter


CONV_METHOD_NAME_PREFIX = 'convert_'


class PropertyValueConverterMeta(type):

    def __new__(mcls, name, bases, dct):
        new_cls = super(PropertyValueConverterMeta, mcls).__new__(mcls, name, bases, dct)
        new_cls_methods = inspect.getmembers(new_cls, predicate=inspect.ismethod)
        new_cls._converters = {
            n.lstrip(CONV_METHOD_NAME_PREFIX): p.__func__
            for n, p in new_cls_methods
            if n.startswith(CONV_METHOD_NAME_PREFIX)
        }
        return new_cls


class PropertyValueConverter(OsPropertyValueConverter, metaclass=PropertyValueConverterMeta):

    _converters = {}

    @classmethod
    def convert(cls, property_name, property_value):
        conv = cls._converters.get(property_name, None)
        return conv(cls, property_value) if conv else property_value

