# -*- coding: utf-8 -*-

import pikuli.uia.adapter


class PatternFactory(object):

    @classmethod
    def init(cls, adapter):
        pass

    @classmethod
    def make_patternt(cls, automation_element, pattern_name):
        pattern_id = pikuli.uia.adapter.Adapter.get_pattern_id(pattern_name)
        pattern_obj = automation_element.GetCurrentPattern(pattern_id)
        return pattern_obj
