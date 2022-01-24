# -*- coding: utf-8 -*-

'''
   Region - прямоугольная область экрана, которая определяется координатами левого верхнего угла, шириной и высотой.
   Region не содержит информации о визуальном контенте (окна, изображения, текст и т д).
   Контент может быть определен с поомощью методов Region.find() или Region.findAll(), которым передается объект класса Pattern (прямоугольная пиксельная область).
   Эти методы возвращают объект класса Match (потомок Region), имеющим те же свойства и методы, что и Region. Размеры Match равны размерам Pattern, используемого для поиска.
'''
import os
import traceback
from collections import namedtuple

from pikuli.geom.simple_types import Rectangle

if os.name == 'nt':
    import win32gui

from pikuli import FailExit, PikuliError, logger
from pikuli._functions import take_screenshot, highlight_region, SimpleImage

from .location import Location
from .vector import RelativeVec
from .simple_types import Rectangle

RELATIONS = ['top-left', 'center']

class Region(Rectangle):

    _make_cv_methods_class_instance = None

    def __eq__(self, other):
        return (self.x, self.y, self.w, self.h) == (other.x, other.y, other.w, other.h)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __contains__(self, is_contaned):
        """
        Точка или прямоугольник `is_contaned` полностью (всеми углами) внутри `self`.
        """
        if isinstance(is_contaned, Location):
            return ((self.x <= is_contaned.x <= self.x + self.w) and
                    (self.y <= is_contaned.y <= self.y + self.h))
        elif isinstance(is_contaned, Region):
            return (is_contaned.top_left in self) and (is_contaned.bottom_right in self)
        else:
            raise Exception('__contains__(): Unsupported is_contaned = {!r}. self = {!r}'.format(
                is_contaned, self))

    def __lt__(self, other):
        """
        :param other: Второй прямоугольник
        :return: Проверяет, является ли один прямоугольник строго меньше второго по обоим измерениям
        """
        return self.w < other.w and self.h < other.h

    def __le__(self, other):
        """
        :param other: Второй прямоугольник
        :return: Проверяет, является ли один прямоугольник меньше либо равно второго по обоим измерениям
        """
        return self.w <= other.w and self.h <= other.h

    def __gt__(self, other):
        """
        :param other: Второй прямоугольник
        :return: Проверяет, является ли один прямоугольник строго больше второго по обоим измерениям
        """
        return self.w > other.w and self.h > other.h

    def __ge__(self, other):
        """
        :param other: Второй прямоугольник
        :return: Проверяет, является ли один прямоугольник больше либо равно второго по обоим измерениям
        """
        return self.w >= other.w and self.h >= other.h

    def __str__(self):
        return '<Region ({}, {}, {}, {})>'.format(self.x, self.y, self.w, self.h)

    def __init__(self, *args, **kwargs):
        '''
        - Конструктор области. -

        Вариант вызова №1:
            args[0]:
                объект типа Region
                или Screen         -- копируем уже имеющуюуся область-прямоуголник

        Вариант вызова №2:
            args[0:4] == [x, y, w, h]:
                целые числа        -- координаты x,y (угла или центра - см. ниже 'relation'), ширина w, высота h; строим новую область-прямоуголник.
                                      Ширина и высота в пикселях. Крайние пиксели принадлежат области прямоуголника.

        Для всех вариантов вызова есть kwargs:
            relation          -- Как интепретировать смысл точки (x,y):
                'top-left'        - x,y являются координатам левого верхнего угла области-прямоуголника; область строится от этой точки (вариант по умолчанию)
                'center'          - x,y являются координатам центра области-прямоуголника; область строится от этой точки
                None              - выбрать вариант по умолчанию, что равносильно отстуствию параметра 'relation' в kwargs
            title             -- Идентификатор для человека (просто строка)
            id                -- Идентификатор для использования в коде
            winctrl           -- None или указатель на экземпляр класса HWNDElement
            main_window_hwnd  --  Если не указан, но этот регион наследуется от другого региона, то пробуем взять оттуда. Если нет ничего, то
                                  определям hwnd главного окна (сразу после рабочего стола в деревер окон) под цетром прямоуголника. Если прямоугольник
                                  поверх рабочего стола, то будет hwnd = 0.
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
        self.drag_location = None

        # "Объявляем" переменные, которые будут заданы ниже через self.setRect(...):
        super(Region, self).__init__(None, None, None, None)
        self._last_match = None
        self.__stored_image = None

        self._title = None                 # Идентификатор для человека.
        if 'title' in kwargs:
            try:
                self._title = str(kwargs['title'])
            except Exception:
                self._title = repr(kwargs['title'])
        self._id           = kwargs.get('id', None)  # Идентификатор для использования в коде.
        self._winctrl      = kwargs.get('winctrl', None)

        # # Здесь будет храниться экземпляр класса winforms, если Region найдем с помощью win32api:
        # self.winctrl = winforms.HWNDElement()

        try:
            self.setRect(*args, **kwargs)
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'Region\' class constructor call:\n\targs = %s\n\tkwargs = %s' % (traceback.format_exc(), str(args), str(kwargs)))

    @property
    def cv(self):
        if not self._make_cv_methods_class_instance:
            raise PikuliError('Computer Vision (CV) methods aren\'t avaiable.')
        return self._make_cv_methods_class_instance(self)

    def get_id(self):
        return self._id

    def set_id(self, id):
        self._id = id

    def winctrl(self):
        return self._winctrl

    def set_x(self, x, relation='top-left'):
        ''' 'top-left' -- x - координата угла; 'center' -- x - координата цента '''
        if isinstance(x, int) and (relation is None or relation in RELATIONS):
            if relation is None or relation == 'top-left':
                self._x = x
            elif relation == 'center':
                self._x = x - self._w/2
        else:
            raise FailExit('[error] Incorect Region.set_x(...) method call:\n\tx = %s, %s\n\trelation = %s' % (str(x), type(x), str(relation)))

    def set_y(self, y, relation='top-left'):
        ''' 'top-left' -- y - координата угла; 'center' -- у - координата цента '''
        if isinstance(y, int) and (relation is None or relation in RELATIONS):
            if relation is None or relation == 'top-left':
                self._y = y
            elif relation == 'center':
                self._y = y - self._h/2
        else:
            raise FailExit('[error] Incorect Region.set_y(...) method call:\n\ty = %s, %s\n\trelation = %s' % (str(y), type(y), str(relation)))

    def set_w(self, w, relation='top-left'):
        ''' 'top-left' -- не надо менять x; 'center' --  не надо менять x '''
        if isinstance(w, int) and w > 0 and (relation is None or relation in RELATIONS):
            if relation == 'center':
                self._x = self._x + (self._w - w)/2
            self._w = w
        else:
            raise FailExit('[error] Incorect Region.set_w(...) method call:\n\tw = %s, %s\n\trelation = %s' % (str(w), type(w), str(relation)))

    def set_h(self, h, relation='top-left'):
        ''' 'top-left' -- не надо менять y; 'center' --  не надо менять y '''
        if isinstance(h, int) and h > 0 and (relation is None or relation in RELATIONS):
            if relation == 'center':
                self._y = self._y + (self._h - h)/2
            self._h = h
        else:
            raise FailExit('[error] Incorect Region.set_h(...) method call:\n\th = %s, %s\n\trelation = %s' % (str(h), type(h), str(relation)))


    def setRect(self, *args, **kwargs):
        try:
            if len(args) == 1 and isinstance(args[0], Region):
                self.__set_from_Region(args[0])

            elif len(args) == 4:
                args = list(args)
                try:
                    for i in range(4):
                        try:
                            args[i] = int(args[i])
                        except ValueError as ex:
                            raise FailExit('Region.setRect(...): can not tranform to integer args[%i] = %s' %(i, repr(args[i])))

                    if args[2] < 0 or args[3] < 0:
                        raise FailExit('Region.setRect(...): args[2] < 0 or args[3] < 0:')
                except OverflowError:
                    pass

                relation = kwargs.get('relation', 'top-left')
                if relation is None:
                    relation = 'top-left'
                elif relation not in RELATIONS:
                    raise FailExit('#2')

                self._w = args[2]
                self._h = args[3]
                if relation == 'top-left':
                    self._x = args[0]
                    self._y = args[1]
                elif relation == 'center':
                    self._x = args[0] - self._w/2
                    self._y = args[1] - self._h/2
            else:
                raise FailExit('#3')

        except FailExit as e:
            raise FailExit('[error] Incorect \'setRect()\' method call:\n\targs = %s\n\tkwargs = %s\n\tadditional comment: %s' % (str(args), str(kwargs), str(e)))

    def __set_from_Region(self, reg):
        self._x = reg.x
        self._y = reg.y
        self._w = reg.w
        self._h = reg.h

    def offset(self, *args, **kwargs):
        '''
        Возвращает область, сдвинутую, относительно self.
        Вериант №1 (как в Sikuli):
            loc_offs := args[0]  --  тип Location; на сколько сдвинуть; (w,h) сохраняется
        Вериант №2:
            x_offs := args[0]  --  тип int; на сколько сдвинуть; w сохраняется
            y_offs := args[1]  --  тип int; на сколько сдвинуть; h сохраняется
        '''
        if len(kwargs) != 0:
            raise FailExit('[error] Unknown keys in kwargs = %s' % str(kwargs))

        if len(args) == 2 and (isinstance(args[0], int) or isinstance(args[0], float)) and (isinstance(args[1], int) or isinstance(args[1], float)):
            return Region(self._x + int(args[0]), self._y + int(args[1]), self._w, self._h)
        elif len(args) == 1 and isinstance(args[0], Location):
            return Region(self._x + args[0]._x, self._y + args[0]._y, self._w, self._h)
        else:
            raise FailExit('[error] Incorect \'offset()\' method call:\n\targs = %s' % str(args))

    def right(self, l=None):
        ''' Возвращает область справа от self. Self не включено. Высота новой области совпадает с self. Длина новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
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
                scr = Screen('virt')
                reg = Region(self._x, self._y + self._h, self._w, (scr.y + scr.h - 1) - (self._y + self._h) + 1)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x, self._y + self._h, self._w, l)
            # elif isinstance(l, Region):  --  TODO: до пересечения с ... Если внутри или снаружи.
            else:
                raise FailExit()
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'below()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        return reg

    def nearby(self, l=0):
        ''' Возвращает область воукруг self. Self включено. Ширина новой области совпадает с self. Высота новой области len или до конца экрана, если len не задана. '''
        try:
            if isinstance(l, int):
                if (l >= 0) or (l < 0 and (-2*l) < self._w and (-2*l) < self._h):
                    reg = Region(self._x - l, self._y - l, self._w + 2*l, self._h + 2*l)
                else:
                    raise FailExit()
            else:
                raise FailExit()
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'nearby()\' method call:\n\tl = %s' % (traceback.format_exc(), str(l)))
        return reg

    def getTopLeft(self, x_offs=0, y_offs=0):
        """ Устарело """
        return Location(self._x + x_offs, self._y + y_offs)

    def getCenter(self, x_offs=0, y_offs=0):
        """ Устарело """
        return Location(self._x + x_offs + self._w/2, self._y + y_offs + self._h/2)

    @property
    def top_left(self):
        return Location(self._x, self._y)

    @property
    def top_right(self):
        return Location(self._x + self._w - 1, self._y)

    @property
    def bottom_left(self):
        return Location(self._x, self._y + self._h - 1)

    @property
    def bottom_right(self):
        return Location(self._x + self._w - 1, self._y + self._h - 1)

    @property
    def center(self):
        return Location(self._x + self._w/2, self._y + self._h/2)

    @property
    def size(self):
        return (self.w, self.h)

    def take_screenshot(self) -> SimpleImage:
        return take_screenshot(self)

    def click(self, after_click_delay=0, p2c_notif=True):
        self.center.click(after_cleck_delay=after_click_delay, p2c_notif=False)
        if p2c_notif:
            logger.info('pikuli.%s.click(): click in center of %s' % (type(self).__name__, str(self)))

    def rightClick(self, after_cleck_delay=0, p2c_notif=True):
        self.center.rightClick(after_cleck_delay=after_cleck_delay)
        if p2c_notif:
            logger.info('pikuli.%s.rightClick(): right click in center of %s' % (type(self).__name__, str(self)))

    def doubleClick(self, after_cleck_delay=0, p2c_notif=True):
        self.center.doubleClick(after_cleck_delay=after_cleck_delay)
        if p2c_notif:
            logger.info('pikuli.%s.doubleClick(): double click in center of %s' % (type(self).__name__, str(self)))

    def type(self, text, modifiers=None, click=True, press_enter=False, p2c_notif=True):
        ''' Не как в Sikuli '''
        self.center.type(
            text,
            modifiers=modifiers,
            press_enter=press_enter,
            click=click,
            p2c_notif=False)
        if p2c_notif:
            logger.info('pikuli.%s.type(): \'%s\' was typed in center of %s; click=%s, modifiers=%s' % (type(self).__name__, repr(text), str(self), str(click), str(modifiers)))

    def enter_text(self, text, modifiers=None, click=True, p2c_notif=True, press_enter=True):
        ''' Не как в Sikuli '''
        self.center.enter_text(text, modifiers=modifiers, click=click, p2c_notif=False, press_enter=press_enter)
        if p2c_notif:
            logger.info('pikuli.%s.enter_text(): \'%s\' was entred in center of %s; click=%s, modifiers=%s' % (type(self).__name__, repr(text), str(self), str(click), str(modifiers)))

    def scroll(self, direction, count, click=True, modifiers=None, p2c_notif=True):
        self.center.scroll(direction, count, click=click, modifiers=modifiers)
        if p2c_notif:
            logger.info('pikuli.%s.scroll(): scroll in center of %s; direction=%s, count=%s, click=%s' % (type(self).__name__, str(self), str(direction), str(count), str(click)))

    def dragto(self, *dest_location, **kwargs):
        '''
        Перемащает регион, хватая мышкой его центр.
            dest_location -- это tuple из двух координат (x,y) или объект типа Location.

            kwargs:
                p2c_notif  --  _True_|False печатать на экран об этом дейтсвии.
        '''
        p2c_notif = kwargs.pop('p2c_notif', True)
        if len(kwargs) != 0:
            raise Exception('Illegal arguments of pikuli.Region.dragto(): %s' % str(kwargs))

        if self.drag_location is None:
            self.drag_location = self.center
        self.drag_location.dragto(*dest_location)

        # Изменим у текущего объект координаты, т.к. его передвинули:
        center = self.center
        if p2c_notif:
            logger.info('pikuli.%s.dragto(): drag center of %s to (%i,%i)' % (type(self).__name__, str(self), self.x, self.y))
        self._x += self.drag_location.x - center.x
        self._y += self.drag_location.y - center.y

    def drop(self, p2c_notif=True):
        if self.drag_location is not None:
            self.drag_location.drop()
            self.drag_location = None
            if p2c_notif:
                logger.info('pikuli.%s.drop(): drop %s' % (type(self).__name__, str(self)))

    def dragndrop(self, *dest_location, **kwargs):
        ''' Перемащает регион за его центр. '''
        p2c_notif = kwargs.pop('p2c_notif', True)
        if len(kwargs) != 0:
            raise Exception('Illegal arguments of pikuli.Region.dragndrop(): %s' % str(kwargs))

        if self.drag_location is None:
            self.drag_location = self.center
        self.dragto(*dest_location)
        self.drop()
        if p2c_notif:
            logger.info('pikuli.%s.dragto(): drag center of %s to (%i,%i) and drop' % (type(self).__name__, str(self), self.x, self.y))

    def highlight(self, delay=1.5):
        highlight_region(self._x, self._y, self._w, self._h, delay)

    def rel2abs(self, *args):
        """
        Переводит координаты из абсолютной в относительную по формуле:
            x = x0  +  x' / 100 * w
            y = y0  +  y' / 100 * h
        (x0, y0) - абсолютные координаты в пикселях левого верхнего угла ограничивающего прмоугольника.

        :param args: x' в формуле
        :param y_rel: y' в формуле
        :return: :class:`Location`
        """
        rel = RelativeVec(*args)
        return Location.from_rel(self, rel)

    def abs2rel(self, *args):
        """
        Переводит координаты из относительной в абсолютную по формуле:
            x' = (x - x0) * 100 / w
            y' = (y - y0) * 100 / h
        (x0, y0) - абсолютные координаты в пикселях левого верхнего угла ограничивающего прмоугольника.

        :param args: Что-то, из чего может быть создат экземпляр :class:`Location` (точка с
                     абсолютными координатами в пикселях).
        :return: :class:`RelativeVec` контейнер, который содержит в себе относительные координаты
        """
        loc = Location(*args)
        loc.base_reg = self
        return loc.rel

    def is_visible(self):
        return not (isinstance(self.x, float) and isinstance(self.y, float) and isinstance(self.h, float) and isinstance(self.w, float))
