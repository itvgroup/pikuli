# -*- coding: utf-8 -*-
from pikuli.uia.adapter import Enums

from .exceptions import AdapterException


class UiaPatternMethod(object):
    '''
    Wrapper class for UIA pattern method
    (code from https://github.com/xcgspring/AXUI)
    '''
    def __init__(self, function_object, name, args_expected=None):
        if args_expected is None:
            args_expected = []

        self.function_object = function_object
        self.name = name
        self.args = []
        self.outs = []
        for arg in args_expected:
            arg_direction = arg[0]
            arg_type = arg[1]
            arg_name = arg[2]
            if arg_direction == "in":
                self.args.append([arg_type, arg_name])
            elif arg_direction == "out":
                self.outs.append([arg_type, arg_name])
            else:
                # skip unsupported arg_direction
                raise AdapterException("Unsupported arg_direction: %s" % arg_direction)

    def __repr__(self):
        docstring = "Name:\t"+self.name+"\n"
        argument_string = "+ Arguments: +\n"
        for argument in sorted(self.args):
            argument_type = argument[0]
            argument_name = argument[1]

            if argument_type == "POINTER(IUIAutomationElement)":
                argument_type = "UIAElement"
            elif hasattr(Enums, argument_type):
                argument_type = getattr(Enums, argument_type)

            argument_string += "  Name:\t"+argument_name+"\n"
            argument_string += "  Type:\t"+repr(argument_type)+"\n\n"

        return_string = "+ Returns: +\n"
        for out in sorted(self.outs):
            return_name = out[1]
            return_type = out[0]
            return_string += "  Name:\t"+return_name+"\n"
            return_string += "  Type:\t"+return_type+"\n\n"

        docstring += argument_string
        docstring += return_string

        return docstring

    def __call__(self, *in_args):
        '''
        For output value, use original value
        For input arguments:
            1. If required argument is an enum, check if input argument fit requirement
            2. If required argument is "POINTER(IUIAutomationElement)", we accept UIAElement object,
               get required pointer object from UIAElement, and send it to function
            3. Other, no change
        '''
        args = list(in_args)
        if len(self.args) != len(args):
            # LOGGER.warn("Input arguments number not match expected")
            return None
        for index, expected_arg in enumerate(self.args):
            expected_arg_type = expected_arg[0]
            if expected_arg_type == "POINTER(IUIAutomationElement)":
                # get the UIAElment
                args[index] = args[index]._automation_element
            elif hasattr(Enums, expected_arg_type):
                enum = getattr(Enums, expected_arg_type)

                # enum should be an int value, if argument is a string, should translate to int
                if args[index] in enum.__members__:
                    args[index] = enum.__members__[args[index]]

                try:
                    enum(args[index])
                except:
                    # LOGGER.debug("Input argument not in expected value: %s" , args[index])
                    return None

        return self.function_object(*args)
