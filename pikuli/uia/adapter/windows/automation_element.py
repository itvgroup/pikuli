# -*- coding: utf-8 -*-

from pikuli.utils import class_property
from .adapter import Adapter


class AutomationElement(object):

    @class_property
    def RootElement(cls):
        return Adapter._IUIAutomation_obj.GetRootElement()
