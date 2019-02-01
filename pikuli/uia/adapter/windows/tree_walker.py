# -*- coding: utf-8 -*-

import pikuli.uia.adapter


class TreeWalker(object):

    def __init__(self, condition):
        self._walker = pikuli.uia.adapter.Adapter._IUIAutomation_obj.CreateTreeWalker(condition)

    def GetParent(self, automation_element):
        return self._walker.GetParentElement(automation_element)

    def GetFirstChild(self, automation_element):
        return self._walker.GetFirstChildElement(automation_element)

    def GetLastChild(self, automation_element):
        return self._walker.GetLastChildElement(automation_element)

    def GetNextSibling(self, automation_element):
        return self._walker.GetNextSiblingElement(automation_element)

    def GetPreviousSibling(self, automation_element):
        return self._walker.GetPreviousSiblingElement(automation_element)

    def Normalize(self, automation_element):
        return self._walker.NormalizeElement(automation_element)
