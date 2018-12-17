# -*- coding: utf-8 -*-

import ctypes

from pikuli import logger
from ..pattern_description import PatternDescription
from .adapter import Adapter


pattern_interfaces_map = Adapter._build_pattern_interfaces_map(PatternDescription.get_all_names())


class PatternFactory(object):

    @classmethod
    def make_patternt(self, automation_element, pattern_name):
        description = PatternDescription.get_description(pattern_name)
        interface_id = pattern_interfaces_map[pattern_name]

        raw_pointer = automation_element.GetCurrentPatternAs(description.pattern_id, interface_id._iid_)
        if not raw_pointer:
            raise DriverException("Cannot get pattern {}".format(pattern_name))

        pattern_obj = ctypes.POINTER(interface_id)(raw_pointer)
        return pattern_obj
