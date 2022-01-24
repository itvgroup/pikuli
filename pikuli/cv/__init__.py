# -*- coding: utf-8 -*-

from .region_cv_methods import RegionCVMethods
from ..geom import Region as __Region
__Region._make_cv_methods_class_instance = RegionCVMethods

from .file import File
from .match import Match
from .pattern import Pattern
from .screen import Screen
