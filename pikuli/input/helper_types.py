# -*- coding: utf-8 -*-

import os
import traceback
from collections import namedtuple

from pikuli import logger
from pikuli._helpers import NotImplemetedDummyFactory


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

        overriding_dict_name = cls.get_private_name(cls.HOOKED_INIT_CLASS_OVERRIDING)
        overriding_dict = getattr(cls, overriding_dict_name, None)
        if overriding_dict:
            cls.override_unavailable_methods(overriding_dict)

    def init(cls, class_init_method):
        try:
            class_init_method()
        except Exception as ex:
            logger.exception(
                'NOTE: Cann\'t initialize class {!r}. A dummy will be used. '
                'Some features is not available.'.format(cls))
            err_msg = traceback.format_exc()
            cls.mark_as_fail(err_msg)

    def override_unavailable_methods(cls, overriding_dict):
        for _, method_names_list in overriding_dict.items():
            missed_methods = [method_name for method_name in method_names_list if not hasattr(cls, method_name)]
            if missed_methods:
                raise AttributeError('Try to override the followin missig methods in the {!r}: {!r}'.format(
                    cls, missed_methods))

        for failed_cls, err_msg in cls.init_class_failed.items():
            methods_to_override = overriding_dict.get(failed_cls, [])
            for method_name in methods_to_override:
                dummy = NotImplemetedDummyFactory.make_class_method(cls, method_name, err_msg)
                setattr(cls, method_name, dummy)

    def mark_as_fail(cls, err_msg):
        cls.init_class_failed.update({cls: err_msg})

    @property
    def init_class_failed(cls):
        cls._init_class_failed = getattr(cls, '_init_class_failed', {})
        return cls._init_class_failed

    def get_private_name(cls, attr_name):
        return '_{cls_name}{attr_name}'.format(
            cls_name=cls.__name__,
            attr_name=attr_name)


class _HookedClassInit(metaclass=_HookedClassInitMeta):
    pass
