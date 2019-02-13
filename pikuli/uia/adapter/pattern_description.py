# -*- coding: utf-8 -*-

from pikuli import logger
from .patterns_plain_description import METHOD, PROPERTY, patterns_plain_description
from ..exceptions import AdapterException


class PatternDescriptions():

    _pattern_descriptions = {}

    @classmethod
    def init(cls, adapter):
        """
        This methos is aimed to avoid Python circular dependencies.
        """
        for name, plain_desc in patterns_plain_description.items():
            desc = _PattDesc(adapter, name, plain_desc)
            if desc.is_valid:
                cls._pattern_descriptions[desc.pattern_name] = desc
            else:
                logger.debug("Control pattern {} not exist in current UIA namespace".format(desc.pattern_name))

    @classmethod
    def get_description(cls, pattern_name):
        return cls._pattern_descriptions[pattern_name]

    @classmethod
    def get_all_names(cls):
        return cls._pattern_descriptions.keys()


def _unpack_member_description(member_type, member_name, *member_args):
    return member_type, member_name, member_args


class _PattDesc(object):

    def __init__(self, adapter, pattern_name, interface_description):
        self.pattern_name = pattern_name
        self.pattern_id = adapter.try_get_pattern_id(pattern_name)

        self.methods_description = {}
        self.properties_description = {}
        for member_description in (interface_description or []):
            type, name, args = _unpack_member_description(*member_description)
            if type == METHOD:
                self.methods_description[name] = args
            elif type == PROPERTY:
                self.properties_description[name] = args
            else:
                raise AdapterException("Unrecognised type {type!r} in member {member} of pattern {pattern}".format(
                    type=type, member=name, pattern=self.pattern_name))
    @property
    def is_valid(self):
        return (self.pattern_name and self.pattern_id and (self.methods_description or self.properties_description))

    def has_method(self, attr_name):
        return attr_name in self.methods_description

    def has_property(self, attr_name):
        return attr_name in self.properties_description
