from win32con import (IDC_APPSTARTING, IDC_ARROW, IDC_CROSS, IDC_HAND,
    IDC_HELP, IDC_IBEAM, IDC_ICON, IDC_NO, IDC_SIZE, IDC_SIZEALL,
    IDC_SIZENESW, IDC_SIZENS, IDC_SIZENWSE, IDC_SIZEWE, IDC_UPARROW, IDC_WAIT)
from win32gui import LoadCursor, GetCursorInfo

DEFAULT_CURSORS_TYPES = [IDC_APPSTARTING, IDC_ARROW, IDC_CROSS, IDC_HAND,
    IDC_HELP, IDC_IBEAM, IDC_ICON, IDC_NO, IDC_SIZE, IDC_SIZEALL,
    IDC_SIZENESW, IDC_SIZENS, IDC_SIZENWSE, IDC_SIZEWE, IDC_UPARROW, IDC_WAIT]


class MouseCursor(object):

    @classmethod
    def from_current_cursor(cls):
        _, current_cursor_handle, _ = GetCursorInfo()
        return MouseCursor.from_handle(current_cursor_handle)

    @classmethod
    def from_handle(cls, handle):
        for cursor_type in DEFAULT_CURSORS_TYPES:
            if handle == LoadCursor(0, cursor_type):
                return cls(handle=handle, cursor_type=cursor_type)
        raise Exception("Unknown cursor handle {}".format(handle))

    def __init__(self, cursor_type, handle):
        self.type = cursor_type
        self.handle = handle


