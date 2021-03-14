# -*- coding: utf-8 -*-

from .identifer_names import element_property_names, control_type_names
from .helper_types import IdNameMap
from .pattern_description import PatternDescriptions
from .platform_init import OsAdapterMixin


class AdapterMeta(type):

    def __new__(mcls, name, bases, dct):
        cls = super(AdapterMeta, mcls).__new__(mcls, name, bases, dct)

        """
        This code targets to :class:`dotnet.DotNetAdapter` and :class:`win_native.WinAdapter`.
        Build-function are defined in those classses.
        """
        cls._enums = cls._make_enums()

        cls._element_properties_map = IdNameMap(
            cls._build_properties_map, element_property_names)

        cls._properties_of_pattern_availability_map = IdNameMap(
            cls._build_properties_map,
            ["Is{pattern_name}Available".format(pattern_name=n) for n in PatternDescriptions.get_all_known_names()])

        cls._control_type_map = IdNameMap(
            cls._build_control_types_map, control_type_names)

        cls._patterns_map = IdNameMap(
            cls._build_patterns_map, PatternDescriptions.get_all_known_names())

        return cls


class Adapter(OsAdapterMixin, metaclass=AdapterMeta):
    
    known_element_property_names = element_property_names
