# -*- coding: utf-8 -*-

from . import _functions, FailExit, geom


class Screen(geom.region.Region):
    """ Represents physical computer display screen.
        x, y  --  left upper corner coords relative to virtual desktop.
        w, h  --  screen rectangle area dimensions.
        n     --  display number.
    """
    def __init__(self, n):
        self.n = 0 if n == 'virt' else n

        if self.n < 0:
            raise FailExit('Monitor number is less than zero.')

        # Returns a sequence of tuples.
        # For each monitor found, returns a handle to the monitor,
        # device context handle, and intersection rectangle:
        # (hMonitor, hdcMonitor, PyRECT).
        self.__mon_hndl, _, mon_rect = \
            _functions._screen_n_to_mon_descript(self.n)

        super(Screen, self).__init__(mon_rect[0],
                                     mon_rect[1],
                                     mon_rect[2] - mon_rect[0],
                                     mon_rect[3] - mon_rect[1],
                                     title='Screen ({})'.format(self.n))

    def __repr__(self):
        return '<Screen ({}) ({}, {}, {}, {})>'.format(
            self.n, self._x, self._y, self._w, self._h)
