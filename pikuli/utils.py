# -*- coding: utf-8 -*-
import logging
import sys

from pikuli import logger


class class_property(property):

    def __init__(self, method):
        super(class_property, self).__init__(classmethod(method))

    def __get__(self, cls, owner):
        p = self.fget.__get__(cls, owner)
        return p()


def basic_logger_config(loglevel=logging.INFO):
    if logger.handlers:
        logger.info('Pikuli logger already configured. Skip `pikuli.utils.basic_logger_config()`.')
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s.%(msecs).03d] [%(threadName)s] [%(levelname)s] %(name)s %(message)s',
        datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    handler.setLevel(loglevel)

    logger.setLevel(loglevel)
    logger.addHandler(handler)
    logger.debug('Pikuli logger has been configured basicaly')
