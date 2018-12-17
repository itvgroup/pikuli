# -*- coding: utf-8 -*-

from pikuli.utils import class_property
from .adapter import AutomationElement_clr


class AutomationElement(object):

    @class_property
    def RootElement(cls):
        return AutomationElement_clr.RootElement
