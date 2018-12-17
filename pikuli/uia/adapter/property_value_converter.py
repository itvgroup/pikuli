# -*- coding: utf-8 -*-

CONV_METHOD_NAME_PREFIX = 'convert_'


class PropertyValueConverterMeta(type):

    def __new__(mcls, name, bases, dct):
        new_cls = super(PropertyValueConverterMeta, mcls).__new__(mcls, name, bases, dct)
        new_cls._converters = {
            n.lstrip(CONV_METHOD_NAME_PREFIX): p.__func__
            for n, p in dct.items()
            if n.startswith(CONV_METHOD_NAME_PREFIX)
        }
        return new_cls


class PropertyValueConverterBase(object):

    __metaclass__ = PropertyValueConverterMeta

    _converters = {}

    @classmethod
    def convert(cls, property_name, property_value):
        conv = cls._converters.get(property_name, None)
        return conv(cls, property_value) if conv else property_value

