# -*- coding: utf-8 -*-

from .adapter import PatternFactory
from .adapter.pattern_description import PatternDescription
from .pattern_method import UiaPatternMethod


class UiaPattern(object):
    '''
    Wrapper class for UIA pattern interface
    (Based on https://github.com/xcgspring/AXUI)
    '''
    def __init__(self, automation_element, pattern_name):
        self._pattern_object = PatternFactory.make_patternt(automation_element, pattern_name)
        self._pattern_description = PatternDescription.get_description(pattern_name)

    def __getattr__(self, member_name):
        member_object = getattr(self._pattern_object, member_name)

        if self._pattern_description.has_method(member_name):
            return UiaPatternMethod(member_object, member_name, self._methods[member_name])
        elif self._pattern_description.has_property(member_name):
            return member_object
        else:
            raise AttributeError("Pattern attribute {!r} not exist".format(member_name))

    def __str__(self):
        docstring = ""
        docstring += "Properties:\n"
        for property_ in self._properties.items():
            name = property_[0]
            argument = property_[1][0]
            value_type = argument[1]
            value = getattr(self._pattern_object, name)
            docstring += "#"*32+"\n"
            docstring += "  Name:\t"+name+"\n"
            docstring += "  Value Type:\t"+value_type+"\n"
            docstring += "  Value:\t"+repr(value)+"\n"

        docstring += "\nMethods:\n"
        for method_ in self._methods.items():
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
                    elif argument_type in hasattr(enums, argument_type):
                        argument_type = getattr(enums, argument_type)

                    argument_string += "    Name:\t"+argument_name+"\n"
                    argument_string += "    Type:\t"+repr(argument_type)+"\n\n"
                elif argument_direction == "out":
                    return_string += "    Name:\t"+argument_name+"\n"
                    return_string += "    Type:\t"+argument_type+"\n\n"

            docstring += argument_string
            docstring += return_string

        return docstring
