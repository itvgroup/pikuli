# -*- coding: utf-8 -*-

from pikuli import logger
from pikuli.uia import AdapterException
from pikuli.utils import class_property


class AdapterBase(object):

    @class_property
    def Enums(cls):
        """
        Check enum values with the current API version.
        """
        return cls._enums

    @classmethod
    def get_property_id(cls, name):
        id_ = cls.try_get_property_id(name)
        if id_ is None:
            raise AdapterException("Property {!r} is no available".format(name))
        return id_

    @classmethod
    def try_get_property_id(cls, name):
        return (cls._element_properties_map.try_name2id(name) or
                cls._properties_of_pattern_availability_map.try_name2id(name))

    @classmethod
    def get_control_type_id(cls, name):
        id_ = cls.try_get_control_type_id(name)
        if id_ is None:
            raise AdapterException("Control Type {!r} is no available".format(name))
        return id_

    @classmethod
    def try_get_control_type_id(cls, name):
        return cls._control_type_map.try_name2id(name)

    @classmethod
    def get_control_type_name(cls, id_):
        name = cls._control_type_map.try_id2name(id_)
        if name is None:
            raise AdapterException("Control Type id {!r} is no available".format(id_))
        return name

    @classmethod
    def get_pattern_id(cls, name):
        id_ = cls.try_get_pattern_id(name)
        if id_ is None:
            raise AdapterException("Pattern {!r} is no available".format(name))
        return id_

    @classmethod
    def try_get_pattern_id(cls, name):
        return cls._patterns_map.try_name2id(name)

    """
    @classmethod
    def get_pattern_name(cls, id_):
        name = cls._patterns_map.try_id2name(id_)
        if name is None:
            raise AdapterException("Pattern id {!r} is no available".format(id_))
        return name
    """

    @classmethod
    def get_api_property_names(cls):
        """
        Returns all Propoperty names are known in current API.
        """
        return sorted(cls._element_properties_map.names())

    @classmethod
    def _build_map(cls, get_attr_from, name_format, err_msg_preamble, names):
        """
        Is used in derived classes :class:`dotnet.Adapter` and :class:`win_native.Adapter`.
        """
        name2id = {}
        for name in names:
            api_name = name_format.format(name=name)
            id_ = getattr(get_attr_from, api_name, None)
            if id_ is None:
                logger.debug("{preamble} {name} ({api_name}) not exist in current UIA namespace".format(
                    preamble=err_msg_preamble, name=name, api_name=api_name))
                continue
            name2id[name] = id_
        return name2id
