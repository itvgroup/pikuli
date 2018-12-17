# -*- coding: utf-8 -*-

import os
if os.name == 'nt':
    from .windows.adapter import Adapter
    from .windows.automation_element import AutomationElement
    from .windows.condition import Condition
    from .windows.pattern_factory import PatternFactory
    from .windows.tree_walker import TreeWalker
    from .windows.value_converters import PropertyValueConverter
elif os.name == 'posix':
    from .mono.adapter import Adapter
    from .mono.automation_element import AutomationElement
    from .mono.condition import Condition
    from .mono.pattern_factory import PatternFactory
    from .mono.tree_walker import TreeWalker
    from .mono.value_converters import PropertyValueConverter
else:
    raise Exception('Not supported: os.name = {}'.format(os.name))

Enums = Adapter.Enums
