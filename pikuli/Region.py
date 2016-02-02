# -*- coding: utf-8 -*-

'''
   Region - прямоугольная область экрана, которая определяется координатами левого верхнего угла, шириной и высотой.
   Region не содержит информации о визуальном контенте (окна, изображения, текст и т д).
   Контент может быть определен с поомощью методов Region.find() или Region.findAll(), которым передается объект класса Pattern (прямоугольная пиксельная область). 
   Эти методы возвращают объект класса Match (потомок Region), имеющим те же свойства и методы, что и Region. Размеры Match равны размерам Pattern, используемого для поиска. 
'''
import time
import traceback
import cv2
import numpy as np
import _functions
from _exceptions import *
from Pattern import *
from Location import *

RELATIONS = ['top-left', 'center']

DELAY_BETWEEN_CV_ATTEMPT = 0.5      # Время в [c] между попытками распознования графического объекта

class Region(object):

    def __init__(self, *args, **kwargs):  # relation='top-left', title=None):
        '''
        - Конструктор области. -

        Вариант вызова №1:
            args[0]:
                объект типа Region
                или Screen         -- копируем уже имеющуюуся область-прямоуголник

        Вариант вызова №2:
            args[0:4] == [x, y, w, h]:
                целые числа        -- координата x,y, ширина w, высоа h; строим новую область-прямоуголник

        Для всех вариантов вызова есть kwargs:
            relation:
                'top-left' -- x,y являются координатам левого верхнего угла области-прямоуголника; область строится от этой точки
                'center'   -- x,y являются координатам центра области-прямоуголника; область строится от этой точки
            title:
                строка     -- просто строка

        Дополнительная справка:
            Внутренние поля класса:
                _x, _y  --  левый верхнйи угол; будут проецироваться на x, y
                _w, _h  --  ширина и высота; будут проецироваться на w, h
                _last_match  --  хранит последний найденный объект или обоъеты (Match или список Match'ей); доступно через метод getLastMatch()

            Публичные поля класса:
                x, y  --  левый верхнйи угол; будут записываться из _x, _y
                w, h  --  ширина и высота; будут записываться из _w, _h

            Смысл терминов "ширина" и "высота":
                Под этими терминами понимает число пикселей по каждому из измерений, принадлежащих области. "Рамка" тоже входит в область.
                Т.о. нулем эти величины быть не могут. Равенство единице, к примеру, "ширины" означает прямоугольник вырождается в вертикальную линиию
                толщиной в 1 пиксель.

        '''
        self.auto_wait_timeout = 3.0

        # "Объявляем" переменные, которые будут заданы ниже через self.setRect(...):
        (self.x, self.y, self._x, self._y) = (None, None, None, None)
        (self.w, self.h, self._w, self._h) = (None, None, None, None)
        self.title = None
        self._last_match = None

        try:
            if 'title' in kwargs:
                self.title = str(kwargs['title'])
            self.setRect(*args, **kwargs)
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'Region\' class constructor call:\n\targs = %s\n\tkwargs = %s' % (traceback.format_exc(), str(args), str(kwargs)))


    def __str__(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return 'Region (%i, %i, %i, %i)' % (self._x, self._y, self._w, self._h)


    def setX(self, x, relation='top-left'):
        ''' 'top-left' -- x - координата угла; 'center' -- x - координата цента '''
        (self.y, self.w, self.h) = (self._y, self._w, self._h)
        if isinstance(x, int) and relation in RELATIONS:
            if relation == 'top-left':
                self._x = self.x = x
            elif relation == 'center':
                self._x = self.x = x - self._w/2
        else:
            raise FailExit('[error] Incorect \'setX()\' method call:\n\tx = %s\n\trelation = %s' % (str(x), str(relation)))

    def setY(self, y, relation='top-left'):
        ''' 'top-left' -- y - координата угла; 'center' -- у - координата цента '''
        (self.x, self.w, self.h) = (self._x, self._w, self._h)
        if isinstance(y, int) and relation in RELATIONS:
            if relation == 'top-left':
                self._y = self.y = y
            elif relation == 'center':
                self._y = self.y = y - self._h/2
        else:
            raise FailExit('[error] Incorect \'setY()\' method call:\n\ty = %s\n\trelation = %s' % (str(y), str(relation)))

    def setW(self, w, relation='top-left'):
        ''' 'top-left' -- не надо менять x; 'center' --  не надо менять x '''
        (self.x, self.y, self.h) = (self._x, self._y, self._h)
        if isinstance(w, int) and w > 0 and relation in RELATIONS:
            self._w = self.w = w
            if relation == 'center':
                self._x = self.x = self._x - w/2
        else:
            raise FailExit('[error] Incorect \'setW()\' method call:\n\tw = %s' % str(w))

    def setH(self, h, relation='top-left'):
        ''' 'top-left' -- не надо менять y; 'center' --  не надо менять y '''
        (self.x, self.y, self.w) = (self._x, self._y, self._w)
        if isinstance(h, int) and h > 0 and relation in RELATIONS:
            self._h = self.h = h
            if relation == 'center':
                self._y = self.y = self._y - h/2
        else:
            raise FailExit('[error] Incorect \'setH()\' method call:\n\th = %s' % str(h))


    def setRect(self, *args, **kwargs):
        try:
            if len(args) == 1 and (isinstance(args[0], Region) or isinstance(args[0], Screen)):
                self.__set_from_Region(args[0])

            elif len(args) == 4 and isinstance(args[0], int) and isinstance(args[1], int) and isinstance(args[2], int) and isinstance(args[3], int) and args[2] > 0 and args[3] > 0:
                for a in args:
                    if not isinstance(a, int):
                        raise FailExit('#1')

                if 'relation' in kwargs:
                    if kwargs['relation'] not in RELATIONS:
                        raise FailExit('#2')
                    relation = kwargs['relation']
                else:
                    relation = 'top-left'

                self._w = self.w = args[2]
                self._h = self.h = args[3]
                if relation == 'top-left':
                    self._x = self.x = args[0]
                    self._y = self.y = args[1]
                elif relation == 'center':
                    self._x = self.x = x - args[2]/2
                    self._y = self.y = y - args[3]/2
            else:
                raise FailExit('#3')

        except FailExit as e:
            raise FailExit('[error] Incorect \'setRect()\' method call:\n\targs = %s\n\tkwargs = %s\n\tadditional comment: %s' % (str(args), str(kwargs), str(e)))

    def __set_from_Region(self, reg):
        self._x = self.x = reg.x
        self._y = self.y = reg.y
        self._w = self.w = reg.w
        self._h = self.h = reg.h


    def getX(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return self._x

    def getY(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return self._y

    def getW(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return self._w

    def getH(self):
        (self.x, self.y, self.w, self.h) = (self._x, self._y, self._w, self._h)
        return self._h


    def offset(self, *args):
        ''' Возвращает область, сдвинутую, относительно self.
            Вериант №1 (как в Sikuli):
                loc_offs := args[0]  --  тип Location; на сколько сдвинуть; (w,h) сохраняется
            Вериант №2:
                x_offs := args[0]  --  тип int; на сколько сдвинуть; w сохраняется
                y_offs := args[1]  --  тип int; на сколько сдвинуть; h сохраняется
        '''
        if len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], int):
            return Region(self._x + args[0], self._y + args[1], self._w, self._h)
        elif len(args) == 1 and isinstance(args[0], Location):
            return Region(self._x + args[0]._x, self._y + args[0]._y, self._w, self._h)
        else:
            raise FailExit('[error] Incorect \'offset()\' method call:\n\targs = %s' % str(args))

    def right(self, l=None):
        ''' Возвращает область справа от self. Self не включено. Высота новой области совпадает с self. Длина новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
                #scr = Screen(_scr_num_of_point(self._x, self._y))
                scr = Screen('virt')
                reg = Region(self._x + self._w, self._y, (scr.x + scr.w - 1) - (self._x + self._w) + 1, self._h)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x + self._w, self._y, l, self._h)
            # elif isinstance(l, Region):  --  TODO: до пересечения с ... Если внутри или снаружи.
            else:
                raise FailExit('type of \'l\' is %s; l = %s', (str(type(l)), str(l)))
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'right()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        return reg

    def left(self, l=None):
        ''' Возвращает область слева от self. Self не включено. Высота новой области совпадает с self. Длина новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
                #scr = Screen(_scr_num_of_point(self._x, self._y))
                scr = Screen('virt')
                reg = Region(scr.x, self._y, (self._x - 1) - scr.x + 1, self._h)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x - l, self._y, l, self._h)
            # elif isinstance(l, Region):  --  TODO: до пересечения с ... Если внутри или снаружи.
            else:
                raise FailExit()
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'left()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        return reg

    def above(self, l=None):
        ''' Возвращает область сверху от self. Self не включено. Ширина новой области совпадает с self. Высота новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
                #scr = Screen(_scr_num_of_point(self._x, self._y))
                scr = Screen('virt')
                reg = Region(self._x, scr.y, self._w, (self._y - 1) - scr.y + 1)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x, self._y - l, self._w, l)
            # elif isinstance(l, Region):  --  TODO: до пересечения с ... Если внутри или снаружи.
            else:
                raise FailExit()
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'above()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        return reg

    def below(self, l=None):
        ''' Возвращает область снизу от self. Self не включено. Ширина новой области совпадает с self. Высота новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
                #scr = Screen(_scr_num_of_point(self._x, self._y))
                scr = Screen('virt')
                reg = Region(self._x, self._y + self._h, self._w, (scr.y + scr.h - 1) - (self._y + self._h) + 1)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x, self._y + self._h, self._w, l)
            # elif isinstance(l, Region):  --  TODO: до пересечения с ... Если внутри или снаружи.
            else:
                raise FailExit()
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'below()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        p2c(str(reg))
        return reg


    def getTopLeft(self):
        return Location(self._x, self._y)

    def getTopRight(self):
        return Location(self._x, self._y + self._w - 1)

    def getBottomLeft(self):
        return Location(self._x + self._h - 1, self._y)

    def getBottomRight(self):
        return Location(self._x + self._h - 1, self._y + self._w - 1)

    def getCenter(self):
        return Location(self._x + self._w/2, self._y + self._h/2)


    def __get_field_for_find(self):
        return _functions._grab_screen(self._x, self._y, self._w, self._h)

    def __find(self, ps, field):
        CF = 0
        if CF == 0:
            res = cv2.matchTemplate(field, ps._cv2_pattern, cv2.TM_CCORR_NORMED)
            loc = np.where(res > ps.getSimilarity())  # 0.995
        elif CF == 1:
            res = cv2.matchTemplate(field, ps._cv2_pattern, cv2.TM_SQDIFF_NORMED)
            loc = np.where(res < 1.0 - ps.getSimilarity())  # 0.005

        # for pt in zip(*loc[::-1]):
        #    cv2.rectangle(field, pt, (pt[0] + self._w, pt[1] + self._h), (0, 0, 255), 2)
        # cv2.imshow('field', field)
        # cv2.imshow('pattern', ps._cv2_pattern)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        # 'res' -- Матрица, где каждый элемент содержит корреляуию кусочка "поля" с шаблоном. Каждый элемент
        #          матрицы соответствует пикселю из "поля". Индексация, вестимо, от нуля.
        # 'loc' -- структура вида (array([264, 284, 304]), array([537, 537, 537])) где три пары индексов элементов матрицы 'res',
        #          для которых выполняется условие. Если из zip'нуть, то получиться [(264, 537), (284, 537), (304, 537)].
        # Т.о. каждый tuple в zip'е ниже будет иметь три элемента: индекс по 'x', индекс по 'y' и 'score'.

        '''x_arr = map(lambda x: int(x) + self._x, loc[1])
        y_arr = map(lambda y: int(y) + self._y, loc[0])
        s_arr = map(lambda s: float(s), res[loc[0], loc[1]])
        return zip(x_arr, y_arr, s_arr)'''
        return map(lambda x, y, s: (int(x) + self._x, int(y) + self._y, float(s)), loc[1], loc[0], res[loc[0], loc[1]])


    def findAll(self, ps):
        try:
            if isinstance(ps, str):
                ps = Pattern(ps)
            if not isinstance(ps, Pattern):
                raise FailExit('bad \'ps\' argument; it should be a string (path to image file) or \'Pattern\' object')

            pts = self.__find(ps, self.__get_field_for_find())
            p2c('Pikuli.findAll: try to find %s' % str(ps))
            result = map(lambda pt: Match(pt[0], pt[1], ps._w, ps._h, pt[2], ps.getFilename()), pts)
            p2c('Pikuli.findAll: total found: %s matches' % str(len(result)) )
            return result

        except FailExit as e:
            raise FailExit('[error] Incorect \'findAll()\' method call:\n\tps = %s\n\tadditional comment: %s' % (str(ps), str(e)))


    def _wait_for_appear_or_vanish(self, ps, timeout, aov):
        if isinstance(ps, str):
            ps = Pattern(ps)
        if not isinstance(ps, Pattern):
            raise FailExit('bad \'ps\' argument; it should be a string (path to image file) or \'Pattern\' object')
        if timeout is None:
            timeout = self.auto_wait_timeout
        if not ( (isinstance(timeout, float) or isinstance(timeout, int)) and timeout >= 0 ):
            raise FailExit('bad \'timeout\' argument')

        prev_field = None
        elaps_time = 0
        while True:
            field = self.__get_field_for_find()

            if prev_field is None or (prev_field != field).all():
                pts = self.__find(ps, field)

                if aov == 'appear':
                    if len(pts) != 0:
                        # Что-то нашли. Выреме один вариант с лучшим 'score'. Из несольких с одинаковыми 'score' будет первый при построчном проходе по экрану.
                        pt = max(pts, key=lambda pt: pt[2])
                        return Match(pt[0], pt[1], ps._w, ps._h, pt[2], ps.getFilename())

                elif aov == 'vanish':
                    if len(pts) == 0:
                        return

                else:
                    raise FailExit('unknown \'aov\' = \'%s\'' % str(aov))

            time.sleep(DELAY_BETWEEN_CV_ATTEMPT)
            elaps_time += DELAY_BETWEEN_CV_ATTEMPT
            if elaps_time >= timeout:
                p2c(str(ps))
                raise FindFailed()


    def find(self, ps, timeout=None):
        ''' Ждет, пока паттерн не появится. timeout может быть положительным числом или None. timeout = 0 означает однократную проверку; None -- использование дефолтного значения.
        Возвращает Region, если паттерн появился, и исключение FindFailed, если нет. '''
        p2c('Pikuli.find: try to find %s' % str(ps))
        try:
            reg = self._wait_for_appear_or_vanish(ps, timeout, 'appear')
        except FailExit as e:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'find()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
        else:
            self._last_match = reg
            p2c('Pikuli.find: %s has been found' % str(ps))
            return reg

    def waitVanish(self, ps, timeout=None):
        ''' Ждет, пока паттерн не исчезнет. Если паттерна уже не было к началу выполнения процедуры, то завершается успешно.
        timeout может быть положительным числом или None. timeout = 0 означает однократную проверку; None -- использование дефолтного значения.'''
        try:
            self._wait_for_appear_or_vanish(ps, timeout, 'vanish')
        except FailExit as e:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'waitVanish()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
        except FindFailed:
            p2c(str(ps))
            return False
        else:
            return True


    def exists(self, ps):
        try:
            self._wait_for_appear_or_vanish(ps, 0, 'appear')
        except FailExit as e:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'exists()\' method call:\n\tself = %s\n\tps = %s' % (traceback.format_exc(), str(self), str(ps)))
        except FindFailed:
            p2c(str(ps))
            return False
        else:
            return True


    def wait(self, ps=None, timeout=None):
        ''' Для совместимости с Sikuli. Ждет появления паттерна или просто ждет.
        timeout может быть положительным числом или None. timeout = 0 означает однократную проверку; None -- использование дефолтного значения.'''
        if ps is None:
            if timeout is not None:
                time.sleep(timeout)
        else:
            try:
                reg = self._wait_for_appear_or_vanish(ps, timeout, 'appear')
            except FailExit as e:
                raise FailExit('\nNew stage of %s\n[error] Incorect \'wait()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
            else:
                return reg


    def getLastMatch(self):
        return self._last_match


    def setAutoWaitTimeout(self, timeout):
        if (isinstance(timeout, float) or isinstance(timeout, int)) and timeout >= 0:
            self.auto_wait_timeout = timeout
        else:
            raise FailExit('[error] Incorect \'setAutoWaitTimeout()\' method call:\n\ttimeout = %s' % str(timeout))

    def click(self):
        self.getCenter().click()

    def rightClick(self):
        self.getCenter().rightClick()

    def doubleClick(self):
        self.getCenter().doubleClick()

    def type(self, text, m = None, click = True):
        ''' Не как в Sikuli '''
        self.getCenter().type(text, m, click)

    def enter_text(self, text, click=True):
        ''' Не как в Sikuli '''
        self.getCenter().enter_text(text, click)

from Match import *
from Screen import *