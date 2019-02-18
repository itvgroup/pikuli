# -*- coding: utf-8 -*-

import os

from pikuli.uia.settings import UIA_FORCE_DOTNET


if os.name == 'nt' and not UIA_FORCE_DOTNET:
    from .win_native.adapter import WinAdapter as OsAdapterMixin
    from .win_native.automation_element import AutomationElement
    from .win_native.condition import Condition
    from .win_native.pattern_factory import PatternFactory
    from .win_native.tree_walker import TreeWalker
    from .win_native.value_converters import WinPropertyValueConverter as OsPropertyValueConverter
elif os.name == 'posix' or UIA_FORCE_DOTNET:
    from .dotnet.adapter import DotNetAdapter as OsAdapterMixin
    from .dotnet.automation_element import AutomationElement
    from .dotnet.condition import Condition
    from .dotnet.pattern_factory import PatternFactory
    from .dotnet.tree_walker import TreeWalker
    from .dotnet.value_converters import DotNetPropertyValueConverter as OsPropertyValueConverter
else:
    raise Exception('Not supported: os.name = {}'.format(os.name))
