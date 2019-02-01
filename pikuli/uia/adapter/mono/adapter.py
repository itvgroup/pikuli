# -*- coding: utf-8 -*-

import clr
clr.AddReference("System.Runtime")
clr.AddReference("UIAutomationTypes")  # System.Windows.Automation
clr.AddReference("UIAutomationProvider")  # System.Windows.Automation
clr.AddReference("UIAutomationClient")  # System.Windows.Automation

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

from ..helper_types import Enums
from ..sdk_enums import _get_sdk_enums


class MonoAdapter(object):

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
        names.remove('LegacyIAccessiblePattern')  # .Net (not just Mono) doesn't support `LegacyIAccessiblePattern`.
        return cls._build_map(System.Windows.Automation, "{name}", "Pattern", names)

    @classmethod
    def is_automation_element(cls, obj):
        return isinstance(obj, AutomationElement_clr)
