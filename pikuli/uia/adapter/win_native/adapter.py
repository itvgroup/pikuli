# -*- coding: utf-8 -*-

from comtypes.client import GetModule, CreateObject
import ctypes

from ..adapter_base import AdapterBase
from ..helper_types import Enums
from ..sdk_enums import _get_sdk_enums


UIA_type_lib_IID = '{944DE083-8FB8-45CF-BCB7-C477ACB2F897}'


def _get_enum_element_full_name(elem):
    return '{enum_name}_{elem_name}'.format(
        enum_name=elem.__class__.__name__, elem_name=elem._c_name)


class WinAdapter(AdapterBase):

    _UIA_wrapper = GetModule((UIA_type_lib_IID, 1, 0))  # 'UIAutomationCore.dll'
    _IUIAutomation_obj = None
    _IUIAutomationElement = getattr(_UIA_wrapper, 'IUIAutomationElement', None)

    for __interface_id in [("IUIAutomation2", "CUIAutomation8"), ("IUIAutomation", "CUIAutomation")]:
        __IUIAutomation = getattr(_UIA_wrapper, __interface_id[0], None)
        __CUIAutomation = getattr(_UIA_wrapper, __interface_id[1], None)
        if __IUIAutomation is not None:
            _IUIAutomation_obj = CreateObject(__CUIAutomation, None, None, __IUIAutomation)
            break

    @classmethod
    def _make_enums(cls):
        """ Is called by the ancestor class :class:`AdapterBase`. """
        enums = Enums()
        for enum in _get_sdk_enums():
            # Check if enum name corresponds to an integer constant:
            enum_name_type = getattr(cls._UIA_wrapper, enum.__name__, None)
            if enum_name_type is not ctypes.c_int:
                continue

            for elem in enum:
                api_enum_elem_name = _get_enum_element_full_name(elem)
                api_value = getattr(cls._UIA_wrapper, api_enum_elem_name, None)

                if api_value is None:
                    continue

                if not isinstance(api_value, int):
                    raise Exception('{elem!r}: api_value={val} is not ctypes.c_int'.format(
                        val=api_value, elem=elem))
                if api_value != elem.value:
                    raise Exception('{elem!r}: api_value={api_val} != elem.value={elem_val}'.format(
                        elem=elem, api_value=api_value, elem_val=elem.value))

            enums._add(enum)

        return enums

    @classmethod
    def _build_properties_map(cls, names):
        """ Is called by the ancestor class :class:`AdapterBase`. """
        return cls._build_map(cls._UIA_wrapper, "UIA_{name}PropertyId", "Property", names)

    @classmethod
    def _build_control_types_map(cls, names):
        """ Is called by the ancestor class :class:`AdapterBase`. """
        return cls._build_map(cls._UIA_wrapper, "UIA_{name}ControlTypeId", "Control Type", names)

    @classmethod
    def _build_patterns_map(cls, names):
        """ Is called by the ancestor class :class:`AdapterBase`. """
        return cls._build_map(cls._UIA_wrapper, "UIA_{name}Id", "Pattern", names)

    @classmethod
    def _build_pattern_interfaces_map(cls, names):
        """ Is called by the ancestor class :class:`AdapterBase`. """
        return cls._build_map(cls._UIA_wrapper, "IUIAutomation{name}", "Pattern Interface", names)

    @classmethod
    def is_automation_element(cls, obj):
        return isinstance(obj, cls._IUIAutomationElement)

    @classmethod
    def get_supported_patterns(cls, uia_element):
        return [pattern_name for pattern_name in cls._patterns_map.names()
                if uia_element.get_pattern(pattern_name) is not None]
