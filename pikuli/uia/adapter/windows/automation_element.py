# -*- coding: utf-8 -*-

import pikuli.uia.adapter
from pikuli.utils import class_property


class AutomationElement(object):

    @class_property
    def RootElement(cls):
        return pikuli.uia.adapter.Adapter._IUIAutomation_obj.GetRootElement()
