from .mixin import _ValuePattern_methods
from .uia_control import UIAControl


class ProgressBar(UIAControl, _ValuePattern_methods):

    CONTROL_TYPE = 'ProgressBar'

