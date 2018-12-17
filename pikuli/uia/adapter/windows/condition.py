# -*- coding: utf-8 -*-

from pikuli.utils import class_property
from .adapter import Adapter


class Condition(object):

    @class_property
    def TrueCondition(cls):
        return Adapter._IUIAutomation_obj.CreateTrueCondition()

