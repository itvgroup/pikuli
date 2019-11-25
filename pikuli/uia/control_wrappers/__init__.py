# -*- coding: utf-8 -*-

CONTROL_CHECK_TIMEOUT = 20

from .registred_control_classes import RegisteredControlClasses
RegisteredControlClasses._register_all()

from .desktop import Desktop
