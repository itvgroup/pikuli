# -*- coding: utf-8 -*-

import os
import sys

from ._logger import logger
from ._settings_class import settings

from ._exceptions import PikuliError, FailExit, FindFailed

from .geom.vector import Vector, RelativeVec
from .geom.region import Region
from .geom.location import Location, LocationF

__addImagePath_err_msg = "The directory of the ran py-file cann't be set as images path: {}"
try:
    __main_module = sys.modules['__main__']
    try:
        __main_module_file = __main_module.__file__
    except Exception as __ex1:
        logger.warning(__addImagePath_err_msg.format(__ex1))
    else:
        settings.addImagePath(
            os.path.dirname(os.path.abspath(__main_module_file)))
except Exception as __ex:
    logger.exception(__addImagePath_err_msg.format(__ex))

from . import uia
from . import cv
