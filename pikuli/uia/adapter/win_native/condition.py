# -*- coding: utf-8 -*-

from pikuli.utils import class_property
import pikuli.uia.adapter


class Condition(object):

    @class_property
    def TrueCondition(cls):
        return pikuli.uia.adapter.Adapter._IUIAutomation_obj.CreateTrueCondition()

