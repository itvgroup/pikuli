# -*- coding: utf-8 -*-

import re

import clr

_uia_assembly_names = {
    "short": [
        "UIAutomationTypes",
        "UIAutomationProvider",
        "UIAutomationClient"
    ],
    "full_v4": [
        "UIAutomationTypes, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35",
        "UIAutomationProvider, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35",
        "UIAutomationClient, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35"
    ],
    "full_v3": [
        "UIAutomationTypes, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35",
        "UIAutomationProvider, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35",
        "UIAutomationClient, Version=3.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35"
    ]
}

def _load_uia_assemblies_by_name_type(name_type):
    for assm_name in _uia_assembly_names[name_type]:
        clr.AddReference(assm_name)  # contains System.Windows.Automation


clr.AddReference("System.Runtime")
try:
    _load_uia_assemblies_by_name_type("short")
except:
    _load_uia_assemblies_by_name_type("full_v4")


import System.Windows.Automation
from System.Windows.Automation import (
    AutomationElement as AutomationElement_clr,
    Condition as Condition_clr,
    ControlType as ControlType_clr,
    TreeScope as TreeScope_clr,
    TreeWalker as TreeWalker_clr)

# Enums:
from System import Enum
from System.Windows.Automation import (
    AsyncContentLoadedState,
    AutomationElementMode,
    # AutomationLiveSetting,
    ClientSideProviderMatchIndicator,
    DockPosition,
    ExpandCollapseState,
    # IsOffscreenBehavior,
    OrientationType,
    PropertyConditionFlags,
    RowOrColumnMajor,
    ScrollAmount,
    StructureChangeType,
    SupportedTextSelection,
    # SynchronizedInputType,
    ToggleState,
    TreeScope,
    WindowInteractionState,
    WindowVisualState,
)
from System.Windows.Automation.Provider import (
    NavigateDirection,
    ProviderOptions,
)

from pikuli import logger
from pikuli.utils import class_property

from ..adapter_base import AdapterBase
from ..helper_types import Enums
from ..sdk_enums import _get_sdk_enums


class DotNetAdapter(AdapterBase):

    _AUTOMATION_PATTERN_PROGRAMMATIC_NAME_FORMAT = re.compile(r"(?P<pattern_name>\w+)Identifiers\.Pattern")

    @classmethod
    def _make_enums(cls):
        """ Is called by the ancestor class :class:`AdapterBase`. """
        dotnet_enums = {
            e.__name__: e for e in [
                NavigateDirection,
                ProviderOptions,
                AsyncContentLoadedState,
                AutomationElementMode,
                # AutomationLiveSetting,
                ClientSideProviderMatchIndicator,
                DockPosition,
                ExpandCollapseState,
                # IsOffscreenBehavior,
                OrientationType,
                PropertyConditionFlags,
                RowOrColumnMajor,
                ScrollAmount,
                StructureChangeType,
                SupportedTextSelection,
                # SynchronizedInputType,
                ToggleState,
                TreeScope,
                WindowInteractionState,
                WindowVisualState,
            ]
        }

        # Some Enum's elements are not defined in Mono:
        exceptions = {
            'ProviderOptions': [ 'UseComThreading', 'RefuseNonClientSupport', 'HasNativeIAccessible', 'UseClientCoordinates' ],
        }

        enums = Enums()
        for enum in _get_sdk_enums():
            if enum.__name__ not in dotnet_enums:
                continue

            for elem in enum:
                except_elements = exceptions.get(enum.__name__, list())
                if elem._c_name in except_elements:
                    continue

                api_value = getattr(dotnet_enums[enum.__name__], elem._c_name)

                if api_value is None:
                    continue

                if not isinstance(api_value, int):
                    raise Exception('{elem!r}: api_value={val} is not ctypes.c_int'.format(
                        val=api_value, elem=elem))
                if api_value != elem.value:
                    raise Exception('{elem!r}: api_value={api_val} != elem.value={elem_val}'.format(
                        elem=elem, api_val=api_value, elem_val=elem.value))

            enums._add(enum)

        return enums

    @classmethod
    def _build_properties_map(cls, names):
        """ Is called by the ancestor class :class:`AdapterBase`. """
        return cls._build_map(AutomationElement_clr, "{name}Property", "Property", names)

    @classmethod
    def _build_control_types_map(cls, names):
        """ Is called by the ancestor class :class:`AdapterBase`. """
        return cls._build_map(ControlType_clr, "{name}", "Control Type", names)

    @classmethod
    def _build_patterns_map(cls, names):
        """ Is called by the ancestor class :class:`AdapterBase`. """
        # names.remove('LegacyIAccessiblePattern')  # .Net (not just Mono) doesn't support `LegacyIAccessiblePattern`.
        return cls._build_map(System.Windows.Automation, "{name}Identifiers", "Pattern", names)

    @classmethod
    def is_automation_element(cls, obj):
        return isinstance(obj, AutomationElement_clr)

    @classmethod
    def get_supported_patterns(cls, uia_element):
        ret = []

        automation_pattern_array = uia_element._automation_element.GetSupportedPatterns()

        for automation_pattern in automation_pattern_array:
            m = cls._AUTOMATION_PATTERN_PROGRAMMATIC_NAME_FORMAT.match(automation_pattern.ProgrammaticName)
            if not m:
                continue
            pattern_name = m.group('pattern_name')
            ret.append(pattern_name)

        return ret
