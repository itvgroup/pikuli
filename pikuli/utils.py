# -*- coding: utf-8 -*-

class class_property(property):
    def __init__(self, method):
        super(class_property, self).__init__(classmethod(method))

    def __get__(self, cls, owner):
        p = self.fget.__get__(cls, owner)
        return p()
