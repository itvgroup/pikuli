# -*- coding: utf-8 -*-


class FailExit(Exception):
    ''' Исключение возникает, когда обнаруживается какая-то ошибка: неправильно заданы входные аргумены, что-то не стыкуется в геметрических расчетах и т.п. '''
    pass


class FindFailed(Exception):
    ''' Исключение возникает, когда не нашли изображения на экране. '''
    NOT_FOUND_ERROR = 0
    OPENCV_ERROR    = 1

    def __init__(self, msg, patterns=None, field=None, cause=NOT_FOUND_ERROR):
        super(FindFailed, self).__init__(msg)

        if (patterns is not None) and (field is not None):
            self.patterns = patterns
            self.field    = field
        elif not ((patterns is None) and (field is None)):
            raise Exception('pikuli: \'FindFailed\' exception cunstructing error:\n\tpattern = %s\n\tfield = %s' % (str(patterns), str(field)))
        else:
            self.patterns = None
            self.field    = None

        cause_avail_val = [FindFailed.NOT_FOUND_ERROR, FindFailed.OPENCV_ERROR]
        if cause not in cause_avail_val:
            raise Exception('pikuli: \'FindFailed\' exception cunstructing error:\n\tcause = %s\n\tavailable values = %s' % (str(cause), str(cause_avail_val)))
        self.cause = cause
