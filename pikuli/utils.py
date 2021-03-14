# -*- coding: utf-8 -*-

from datetime import datetime


class class_property(property):

    def __init__(self, method):
        super(class_property, self).__init__(classmethod(method))

    def __get__(self, cls, owner):
        p = self.fget.__get__(cls, owner)
        return p()


def wait_while(f_logic, timeout, warning_timeout=None, warning_text=None, delay_between_attempts=0.5):
    """
    Внутренний цик выполняется, пока вычисление `f_logic()` трактуется как `True`.
    """

    warning_flag = False
    start_time = datetime.now()

    while True:
        try:
            result = f_logic()
        except Exception:
            pass
        else:
            if not result:
                return True

        elaps_time = (datetime.now() - start_time).total_seconds()

        if warning_timeout is not None and elaps_time > warning_timeout and not warning_flag:
            text_addon = '. {}'.format(warning_text) if warning_text else ''
            logger.warning("Waiting time exceeded {}{}".format(warning_timeout, text_addon))
            warning_flag = True

        if timeout is not None and elaps_time > timeout:
            return False

        time.sleep(delay_between_attempts)


def wait_while_not(f_logic, timeout, warning_timeout=None, delay_between_attempts=0.5):
    """
    Внутренний цик выполняется, пока вычисление `f_logic()` трактуется как `False`.
    """

    warning_flag = False
    start_time = datetime.now()
    while True:
        try:
            result = f_logic()
        except Exception:
            pass
        else:
            if result:
                return True

        elaps_time = (datetime.now() - start_time).total_seconds()

        if warning_timeout and elaps_time > warning_timeout and not warning_flag:
            logger.warning("Waiting time exceeded {}".format(warning_timeout))
            warning_flag = True

        if timeout and elaps_time > timeout:
            return False

        time.sleep(delay_between_attempts)