# -*- coding: utf-8 -*-
from pikuli.uia.control_wrappers.mixin import _ValuePattern_methods
from pikuli.uia.control_wrappers.uia_control import UIAControl


class Spinner(UIAControl, _ValuePattern_methods):

    CONTROL_TYPE = 'Spinner'
