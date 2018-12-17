# -*- coding: utf-8 -*-

from .adapter import Adapter


class PatternFactory(object):

    @classmethod
    def make_patternt(cls, automation_element, pattern_name):
        pattern_id = Adapter.get_pattern_id(pattern_name)
        pattern_obj = automation_element.GetCurrentPattern(pattern_id)
        return pattern_obj
