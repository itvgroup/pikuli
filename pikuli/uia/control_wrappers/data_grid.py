# -*- coding: utf-8 -*-

from .uia_control import UIAControl
from .property_grid import ANPropGrid_Table


class DataGrid(ANPropGrid_Table):

    CONTROL_TYPE = 'DataGrid'
