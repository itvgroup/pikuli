# -*- coding: utf-8 -*-

import os


# TODO: Temporary solution. Mono doesn't throw `COMError` exceptions
if os.name == 'nt':
    import _ctypes
    COMError = _ctypes.COMError
else:
    class COMError(Exception): pass


class AdapterException(Exception):
    pass
