# -*- coding: utf-8 -*-

import os
import traceback
from collections import namedtuple

from pikuli import logger


WindowsButtonCode = namedtuple('WindowsButtonCode', ['event_down', 'event_up'])


class _HookedClassInitMeta(type):

    HOOKED_INIT_CLASS_METHODNAME = '__hooked_class_init'
    HOOKED_INIT_CLASS_OVERRIDING = '__hooked_class_init_overriding'

    def __init__(cls, name, bases, dct):
        super(_HookedClassInitMeta, cls).__init__(name, bases, dct)

        class_init_method_name = cls.get_private_name(cls.HOOKED_INIT_CLASS_METHODNAME)
        class_init_method = getattr(cls, class_init_method_name, None)
        if class_init_method:
            cls.init(class_init_method)
        else:
            cls.mark_as_ok()

        if cls.is_marked_fail():
            overriding_list_name = cls.get_private_name(cls.HOOKED_INIT_CLASS_OVERRIDING)
            overriding_list = getattr(cls, overriding_list_name, None)
            if overriding_list:
                cls.override_methods(overriding_list)

    def init(cls, class_init_method):
        try:
            class_init_method()
        except Exception as ex:
            logger.exception(ex,
                'NOTE: Cann\'t initialize class {!r}. A dummy will be used. '
                'Some features is not available.'.format(cls))
            err_msg = traceback.format_exc()
            cls.mark_as_fail(err_msg)
        else:
            cls.mark_as_ok()

    def override_methods(cls, overriding_list):

        for method_name in overriding_list:
            if not hasattr(cls, method_name):
                raise AttributeError('Try to override missig method {!r} in the {!r}'.format(method_name, cls))

            def dummy(self, *args, **kwargs):
                raise NotImplementedError('Method {!r} is unavailable by the following reason:{}{!s}'.format(
                    method_name, os.linesep, cls._init_class_failed_reason))

            setattr(cls, method_name, dummy)

    def mark_as_ok(cls):
        cls._init_class_failed_reason = None
        cls._init_class_failed = False

    def mark_as_fail(cls, err_msg):
        reason = ['  * ' + l.rstrip() for l in err_msg.splitlines()]
        cls._init_class_failed_reason = os.linesep.join(reason)
        cls._init_class_failed = True

    def is_marked_fail(cls):
        return cls._init_class_failed

    def get_private_name(cls, attr_name):
        return '_{cls_name}{attr_name}'.format(
            cls_name=cls.__name__,
            attr_name=attr_name)


class _HookedClassInit(object):

    __metaclass__ = _HookedClassInitMeta
