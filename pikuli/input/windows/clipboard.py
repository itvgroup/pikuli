# -*- coding: utf-8 -*-

import win32clipboard
from pikuli import logger


class WinClipboard(object):

    @classmethod
    def get_text_from_clipboard(cls, p2c_notif=True):
        win32clipboard.OpenClipboard()
        try:
            data = str(win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT))
            # it may be CF_TEXT, CF_UNICODETEXT or others (http://docs.activestate.com/activepython/3.1/pywin32/win32clipboard__GetClipboardData_meth.html)
            if p2c_notif:
                logger.info('pikuli._functions.get_text_from_clipboard(): data = \'{}\''.format(data))
        except Exception as ex:
            logger.error(ex)
            raise
        win32clipboard.CloseClipboard()
        return data

    @classmethod
    def set_text_to_clipboard(cls, data, p2c_notif=True):
        if p2c_notif:
            logger.info('pikuli._functions.set_text_to_clipboard(): data = \'{}\''.format(data))
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(str(data))  # А еще есть SetClipboardData (http://docs.activestate.com/activepython/2.4/pywin32/win32clipboard.html)
        except Exception as ex:
            logger.error(ex)
            raise
        win32clipboard.CloseClipboard()
