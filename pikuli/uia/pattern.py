# -*- coding: utf-8 -*-

from .adapter import PatternFactory, Enums
from .adapter.pattern_description import PatternDescriptions
from .pattern_method import UiaPatternMethod


class UiaPattern(object):
    '''
    Wrapper class for UIA pattern interface
    (Based on https://github.com/xcgspring/AXUI)
    '''
    def __init__(self, automation_element, pattern_name):
        self._pattern_name = pattern_name
        self._pattern_object = PatternFactory.make_patternt(automation_element, pattern_name)
        self._pattern_description = PatternDescriptions.get_description(pattern_name)

    def __getattr__(self, member_name):
        member_object = getattr(self._pattern_object, member_name, None)
        if member_object is None:
            raise AttributeError("Attribute {!r} not found in pattern {!r}".format(member_name, self._pattern_name))

        if self._pattern_description.has_method(member_name):
            ret = UiaPatternMethod(member_object, member_name, self._pattern_description.methods_description[member_name])
        elif self._pattern_description.has_property(member_name):
            ret = member_object

        if ret is None:
            raise AttributeError("Attribute {!r} not found in pattern {!r} (member_object={!r})".format(
                member_name, self._pattern_name, member_object))

        return ret

    def __str__(self):
        docstring = ""
        docstring += "Properties:\n"
        for property_ in self._pattern_description.properties_description.items():
            name = property_[0]
            argument = property_[1][0]
            value_type = argument[1]
            value = getattr(self._pattern_object, name)
            docstring += "#"*32+"\n"
            docstring += "  Name:\t"+name+"\n"
            docstring += "  Value Type:\t"+value_type+"\n"
            docstring += "  Value:\t"+repr(value)+"\n"

        docstring += "\nMethods:\n"
        for method_ in self._pattern_description.methods_description.items():
            name = method_[0]
            arguments = method_[1]
            docstring += "#"*32+"\n"
            docstring += "  Name:\t"+name+"\n"
            argument_string = "  Arguments:\n"
            return_string = "  Return:\n"
            for argument in arguments:
                argument_direction = argument[0]
                argument_type = argument[1]
                argument_name = argument[2]
                if argument_direction == "in":
                    if argument_type == "POINTER(IUIAutomationElement)":
                        argument_type = "UIAElement"
                    elif hasattr(Enums, argument_type):
                        argument_type = getattr(Enums, argument_type)

                    argument_string += "    Name:\t"+argument_name+"\n"
                    argument_string += "    Type:\t"+repr(argument_type)+"\n\n"
                elif argument_direction == "out":
                    return_string += "    Name:\t"+argument_name+"\n"
                    return_string += "    Type:\t"+argument_type+"\n\n"

            docstring += argument_string
            docstring += return_string

        return docstring
