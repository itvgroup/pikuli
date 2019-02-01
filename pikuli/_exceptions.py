# -*- coding: utf-8 -*-

import traceback


class PikuliError(RuntimeError):
    pass


class PostMoveCheck(PikuliError):
    pass


class FailExit(PikuliError):
    pass


class FindFailed(PikuliError):
    """ This exception is raised when an image pattern
        is not found on the screen.
    """
    NOT_FOUND_ERROR = 0
    OPENCV_ERROR = 1

    def __init__(self, msg='[NO TEXT MESSAGE]', patterns=None, field=None, cause=NOT_FOUND_ERROR):
        super(FindFailed, self).__init__(msg)

        if (patterns is not None) and (field is not None):
            if not isinstance(patterns, list):
                patterns = [patterns]
            self.patterns = patterns
            self.field = field
        else:
            self.patterns = None
            self.field = None
        self.cause = cause

        self.raise_tb_str = ''.join(traceback.format_stack()[:-1]).rstrip()  # traceback к точке raise'а

