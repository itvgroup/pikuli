# -*- coding: utf-8 -*-

import os

from pikuli import logger


class NotImplemetedDummyBase(object):
    err_msg = None


class NotImplemetedDummyFactory(object):

    class _AttrPlaceholder(object):
        ph = '{attr!r}'
        def __repr__(self): return self.ph
        def __str__(self): return self.ph
    _attr_placeholder = _AttrPlaceholder()

    @classmethod
    def make_classes(cls, target_cls, msg=None, reason=None, **kwargs):
        err_msg = cls._make_class_err_msg(msg, 'classes', reason, target_cls, **kwargs)
        logger.debug('NOTE: ' + err_msg)
        return [cls._make_class(err_msg) for c in target_cls]

    @classmethod
    def make_class(cls, target_cls, msg=None, reason=None, **kwargs):
        err_msg = cls._make_class_err_msg(msg, 'class', reason, target_cls, **kwargs)
        logger.debug('NOTE: ' + err_msg)
        return cls._make_class(err_msg)

    @classmethod
    def _make_class(cls, err_msg):
        class NotImplemetedDummy(NotImplemetedDummyBase):
            def __getattr__(self, attr):
                raise NotImplementedError(err_msg.format(attr=attr))
        NotImplemetedDummy.err_msg = err_msg
        return NotImplemetedDummy

    @classmethod
    def _make_class_err_msg(cls, msg, msg_class_part, reason, target_cls, **kwargs):
        if msg is None:
            attr_part = ', in particular {attr!r},' if 'attr' in kwargs else ''
            msg = ('All methods' + attr_part + ' of the ' + msg_class_part + ' {target_cls!r} is '
                   'unavailable by the following reason:{linesep}{reason!s}')

        formated_reason = cls.format_reason(reason)

        format_args = dict(
            target_cls=target_cls,
            reason=formated_reason,
            linesep=os.linesep,
            attr=cls._attr_placeholder)
        format_args.update(kwargs)

        err_msg = msg.format(**format_args)
        return err_msg

    @classmethod
    def make_class_method(cls, target_cls, method_name, reason):
        formated_reason = cls.format_reason(reason)
        err_msg = ('Method {!r} of the {!r} is unavailable by the following reason:'
                   '{}{!s}'.format(method_name, type(target_cls).__name__, os.linesep, formated_reason))
        logger.debug('NOTE: ' + err_msg)

        def not_implemeted_dummy(*args, **kwargs):
            raise NotImplementedError(err_msg)

        return staticmethod(not_implemeted_dummy)

    @classmethod
    def format_reason(cls, reason):
        reason_lines = ['  * ' + l.rstrip() for l in (reason or '').splitlines()]
        formatted_reason = os.linesep.join(reason_lines)
        return formatted_reason
