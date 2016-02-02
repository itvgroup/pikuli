# -*- coding: utf-8 -*-

'''
   Screen - представление физических мониторов компьютера. 
'''

import _functions
from _exceptions import *
from Region import *

class Screen(Region):
    ''' Экран.

        x, y  --  координаты левого верхнего угла в системе координат виртуального рабочего стола
        w, h  --  размеры прямоуголника экрана
    '''
    def __init__(self, n):
        if n == 'virt':
            n = 0

        if isinstance(n, int) and n >= 0:
            # Returns a sequence of tuples. For each monitor found, returns a handle to the monitor, device context handle, and intersection rectangle: (hMonitor, hdcMonitor, PyRECT)
            (mon_hndl, _, mon_rect) = _functions._screen_n_to_mon_descript(n)

            super(Screen, self).__init__(mon_rect[0], mon_rect[1], mon_rect[2]-mon_rect[0], mon_rect[3]-mon_rect[1], title='Screen (%i)' % n)
            self.n = self._n = n
            self.__mon_hndl = mon_hndl

        else:
            raise FailExit()

    def __str__(self):
        super(Screen, self).__str__()
        self.n = self._n
        return 'Screen (%i) (%i, %i, %i, %i)' % (self._n, self._x, self._y, self._w, self._h)