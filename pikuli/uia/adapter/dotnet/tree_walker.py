# -*- coding: utf-8 -*-

from pikuli.utils import class_property
from .adapter import TreeWalker_clr


class TreeWalker(object):

    def __init__(self, condition):
        self._walker = TreeWalker_clr(condition)

    def GetParent(self, automation_element):
        return self._walker.GetParent(automation_element)

    def GetFirstChild(self, automation_element):
        return self._walker.GetFirstChild(automation_element)

    def GetLastChild(self, automation_element):
        return self._walker.GetLastChild(automation_element)

    def GetNextSibling(self, automation_element):
        return self._walker.GetNextSibling(automation_element)

    def GetPreviousSibling(self, automation_element):
        return self._walker.GetPreviousSibling(automation_element)

    def Normalize(self, automation_element):
        return self._walker.Normalize(automation_element)
