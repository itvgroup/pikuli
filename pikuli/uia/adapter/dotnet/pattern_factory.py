# -*- coding: utf-8 -*-

import pikuli.uia.adapter

from ..pattern_description import PatternDescriptions


class _PatternWrapper(object):

    def __init__(self, dotnet_pattern_obj):
        self._dotnet_pattern_obj = dotnet_pattern_obj

    def __getattr__(self, attr_name):
        _dotnet_pattern_obj_attr = getattr(self._dotnet_pattern_obj, attr_name, None)
        if _dotnet_pattern_obj_attr is not None:
            return _dotnet_pattern_obj_attr

        mode, property_name = self._split_attr_name(attr_name)
        if not mode or not property_name:
            raise AttributeError('attr_name={!r} is invalid', attr_name)

        info = getattr(self._dotnet_pattern_obj, mode, None)
        if not info:
            raise AttributeError('attr_name={!r} not exist', attr_name)

        property_value = getattr(info, property_name, None)
        if property_value is None:
            raise AttributeError('attr_name={!r} not exist', attr_name)

        return property_value

    def _split_attr_name(self, attr_name):
        for mode in ['Current', 'Cached']:
            if attr_name.startswith(mode):
                return (mode, attr_name[len(mode):])
        return (None, None)


class PatternFactory(object):

    _lazzy_created_wrappers = {}

    @classmethod
    def init(cls, adapter):
        PatternDescriptions.init(adapter)

    @classmethod
    def make_patternt(cls, automation_element, pattern_name):
        pattern_id = pikuli.uia.adapter.Adapter.get_pattern_id(pattern_name)
        pattern_obj = automation_element.GetCurrentPattern(pattern_id.Pattern)
        return _PatternWrapper(pattern_obj)
