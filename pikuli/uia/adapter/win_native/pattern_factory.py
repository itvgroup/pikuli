# -*- coding: utf-8 -*-

import ctypes

from pikuli.uia.exceptions import AdapterException
from ..pattern_description import PatternDescriptions


class PatternFactory(object):

    _pattern_interfaces_map = {}

    @classmethod
    def init(cls, adapter):
        PatternDescriptions.init(adapter)
        pattern_names = PatternDescriptions.get_names()
        cls._pattern_interfaces_map = adapter._build_pattern_interfaces_map(pattern_names)

    @classmethod
    def make_patternt(cls, automation_element, pattern_name):
        description = PatternDescriptions.get_description(pattern_name)
        interface_id = cls._pattern_interfaces_map[pattern_name]

        raw_pointer = automation_element.GetCurrentPatternAs(description.pattern_id, interface_id._iid_)
        if not raw_pointer:
            raise AdapterException("Cannot get pattern {}".format(pattern_name))

        pattern_obj = ctypes.POINTER(interface_id)(raw_pointer)
        return pattern_obj
