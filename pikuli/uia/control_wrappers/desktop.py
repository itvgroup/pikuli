# -*- coding: utf-8 -*-

from ..uia_element import UIAElement


class Desktop(UIAElement):
    '''
    Represents the Desktop. Creating an instance of this class is equal to UIAElement(0).
    '''

    def __init__(self):
        super(Desktop, self).__init__(0)
