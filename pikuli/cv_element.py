# -*- coding: utf-8 -*-

from Region import Region
from Location import Location

class CVElement(object):

    def __init__(self, where_it_is):
        if isinstance(where_it_is, str):
            where_it_is = mwgdb.wdb.get_reg(where_it_is)
        if isinstance(where_it_is, Region):
            self._reg = where_it_is
            where_it_is = where_it_is.getCenter()
        if not isinstance(where_it_is, Location):
            raise Exception('pikuli.cv_element.CVElement.__init__(): input argument must be pikuli.Region or pikuli.Location treating as a center of a spinner, or \"db_class\" path.')
        self._center = where_it_is
        if not hasattr(self, '_reg'):
            self._reg = Region(self._center.x, self._center.y, 1, 1)

    def reg(self):
        #if not hasattr(self, '_reg'):
        #    raise Exception('class pikili.CVElement: You must create _reg field in child classes')
        return self._reg
