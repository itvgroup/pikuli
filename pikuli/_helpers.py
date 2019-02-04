# -*- coding: utf-8 -*-

import os

from pikuli import logger


class NotImplemetedDummyFactory(object):

    class _AttrPlaceholder(object):
        ph = '{attr!r}'
        def __repr__(self): return self.ph
        def __str__(self): return self.ph
    _attr_placeholder = _AttrPlaceholder()

    @classmethod
    def make_class(cls, msg=None, reason=None, target_cls=None, **kwargs):
        if msg is None:
            msg = ('All methods, in particular {attr!r}, of the class {target_cls!r} is '
                   'unavailable by the following reason:{linesep}{reason!s}')

        formated_reason = cls.format_reason(reason)
        format_args = dict(target_cls=target_cls, reason=formated_reason, linesep=os.linesep, attr=cls._attr_placeholder)
        format_args.update(kwargs)
        err_msg = msg.format(**format_args)
        logger.warning('NOTE: ' + err_msg)

        class NotImplemetedDummy(object):
            def __getattr__(self, attr):
                raise NotImplementedError(err_msg.format(attr=attr))

        return NotImplemetedDummy

    @classmethod
    def make_class_method(cls, target_cls, method_name, reason):
        formated_reason = cls.format_reason(reason)
        err_msg = ('Method {!r} of the {!r} is unavailable by the following reason:'
                   '{}{!s}'.format(method_name, type(target_cls).__name__, os.linesep, formated_reason))
        logger.warning('NOTE: ' + err_msg)

        def not_implemeted_dummy(*args, **kwargs):
            raise NotImplementedError(err_msg)

        return staticmethod(not_implemeted_dummy)

    @classmethod
    def format_reason(cls, reason):
        reason_lines = ['  * ' + l.rstrip() for l in (reason or '').splitlines()]
        formatted_reason = os.linesep.join(reason_lines)
        return formatted_reason
