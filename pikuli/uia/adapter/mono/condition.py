# -*- coding: utf-8 -*-

from pikuli.utils import class_property
from .adapter import Condition_clr


class Condition(object):

    @class_property
    def TrueCondition(cls):
        return Condition_clr.TrueCondition
