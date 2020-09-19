# -*- coding: utf-8 -*-

'''
   Region - прямоугольная область экрана, которая определяется координатами левого верхнего угла, шириной и высотой.
   Region не содержит информации о визуальном контенте (окна, изображения, текст и т д).
   Контент может быть определен с поомощью методов Region.find() или Region.findAll(), которым передается объект класса Pattern (прямоугольная пиксельная область).
   Эти методы возвращают объект класса Match (потомок Region), имеющим те же свойства и методы, что и Region. Размеры Match равны размерам Pattern, используемого для поиска.
'''
import time
import traceback
import datetime
import os
import logging
from collections import namedtuple

import cv2
import numpy as np

if os.name == 'nt':
    import win32gui

import pikuli
from pikuli import Settings, FindFailed, FailExit, File

from pikuli._functions import _take_screenshot, verify_timeout_argument, highlight_region
from pikuli.Pattern import Pattern

from .vector import RelativeVec
from .location import Location

#from Match import *
#from Screen import *


RELATIONS = ['top-left', 'center']

# Время в [c] между попытками распознования графического объекта
DELAY_BETWEEN_CV_ATTEMPT = 1.0
DEFAULT_FIND_TIMEOUT = 3.1

from pikuli import logger

def _get_list_of_patterns(ps, failExitText):
    if not isinstance(ps, list):
        ps = [ps]
    for i, p in enumerate(ps):
        try:
            ps[i] = Pattern(p)
        except Exception as ex:
            raise FailExit(failExitText + '\n\t' + ' ' * 20 + str(ex))
    return ps


class Region(object):

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

    def __init__(self, *args, **kwargs):  # relation='top-left', title=None):
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
            find_timeout      --  Значение по умолчанию, которове будет использоваться, если метод find() (и подобные) этого класса вызван без явного указания timeout.
                                  Если не передается конструктуру, то берется из переменной модуля DEFAULT_FIND_TIMEOUT.
                                  Будет наслодоваться ко всем объектам, которые возвращаются методами этого класса.

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
        (self._x, self._y, self._w, self._h) = (None, None, None, None)
        self._last_match = None
        self._image_at_some_moment = None

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
        self._find_timeout = verify_timeout_argument(kwargs.get('find_timeout', DEFAULT_FIND_TIMEOUT), err_msg='pikuli.%s.__init__()' % type(self).__name__)  # Перезапишет, если создавали объект на основе существующего Region

        if os.name == 'nt':
            self._main_window_hwnd = kwargs.get('main_window_hwnd', None)
            if self._main_window_hwnd is None and len(args) == 1:
                self._main_window_hwnd = args[0]._main_window_hwnd
            if self._main_window_hwnd is None :
                w = win32gui.WindowFromPoint((self._x + self._w // 2, self._y + self._h // 2))
                self._main_window_hwnd = pikuli.hwnd.hwnd_element._find_main_parent_window(w)
        else:
            self._main_window_hwnd = None

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
            if len(args) == 1 and (isinstance(args[0], Region) or isinstance(args[0], Screen)):
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
        self._find_timeout = reg._find_timeout

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def w(self):
        return self._w

    @property
    def h(self):
        return self._h

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
            return Region(self._x + int(args[0]), self._y + int(args[1]), self._w, self._h, find_timeout=self._find_timeout)
        elif len(args) == 1 and isinstance(args[0], Location):
            return Region(self._x + args[0]._x, self._y + args[0]._y, self._w, self._h, find_timeout=self._find_timeout)
        else:
            raise FailExit('[error] Incorect \'offset()\' method call:\n\targs = %s' % str(args))

    def right(self, l=None):
        ''' Возвращает область справа от self. Self не включено. Высота новой области совпадает с self. Длина новой области len или до конца экрана, если len не задана. '''
        try:
            if l is None:
                scr = Screen('virt')
                reg = Region(self._x + self._w, self._y, (scr.x + scr.w - 1) - (self._x + self._w) + 1, self._h, find_timeout=self._find_timeout)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x + self._w, self._y, l, self._h, find_timeout=self._find_timeout)
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
                reg = Region(scr.x, self._y, (self._x - 1) - scr.x + 1, self._h, find_timeout=self._find_timeout)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x - l, self._y, l, self._h, find_timeout=self._find_timeout)
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
                reg = Region(self._x, scr.y, self._w, (self._y - 1) - scr.y + 1, find_timeout=self._find_timeout)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x, self._y - l, self._w, l, find_timeout=self._find_timeout)
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
                reg = Region(self._x, self._y + self._h, self._w, (scr.y + scr.h - 1) - (self._y + self._h) + 1, find_timeout=self._find_timeout)
            elif isinstance(l, int) and l > 0:
                reg = Region(self._x, self._y + self._h, self._w, l, find_timeout=self._find_timeout)
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
                    reg = Region(self._x - l, self._y - l, self._w + 2*l, self._h + 2*l, find_timeout=self._find_timeout)
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
    def wh(self):
        return (self.w, self.h)

    def __get_field_for_find(self):
        return self.get_raw_screenshot()

    def get_current_image(self):
        ''' Возвращает текущий скриншот региона в виде картинки. В душе -- это np.array. '''
        return self.__get_field_for_find()

    def is_image_equal_to(self, img):
        ''' Проверяет, что текущее изображение на экране в области (x,y,w,h) совпадет с
        картинкой img в формате np.array, передаваеймо в функцию как рагумент. '''
        return np.array_equal(self.__get_field_for_find(), img)

    def store_current_image(self):
        ''' Сохраняет в поле класса картинку с экрана из области (x,y,w,h). Формат -- numpu.array. '''
        self._image_at_some_moment = self.__get_field_for_find()

    def clear_sored_image(self):
        ''' Очищает сохраненную в классе картинку. '''
        self._image_at_some_moment = None  # TODO: вставить delete ???

    def is_image_changed(self, rewrite_stored_image=False):
        ''' Изменилась ли картинка на экране в регионе с момента последнего вызова этой фукнции
        или self.store_current_image()? Отвечаем на этот вопрос путем сравнения сохраненной в классе
        картинки с тем, что сейчас изоюражено на экране.
        В зависости от аргумента rewrite_stored_image обновим или нет картинку, сохраненную в классе. '''
        img = self.__get_field_for_find()
        eq  = (self._image_at_some_moment is not None) and np.array_equal(img, self._image_at_some_moment)
        if rewrite_stored_image:
            self._image_at_some_moment = img
        return (not eq)

    def _save_as_prep(self, full_filename, format_, msg, msg_loglevel):
        if format_ not in ['jpg', 'png']:
            logger.error('[INTERNAL] Unsupported format_={!r} at call of '
                         'Region._save_as_prep(...). Assume \'png\''.format(format_))
            format_ = 'png'
        if msg_loglevel not in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]:
            logger.warning('[INTERNAL] Unavailable msg_loglevel={!r} at call of '
                           'Region.save_as_{}(...). Assume INFO level.'.format(msg_loglevel, format_))
            msg_loglevel = logging.INFO

        path = os.path.abspath(full_filename)

        full_msg = 'pikuli.Region.save_as_{}:\n\tinput:     {}\n\tfull path: [[f]]'.format(format_, self)
        if msg:
            full_msg = msg + '\n' + full_msg
        logger.log(msg_loglevel, full_msg, extra={'f': File(path)})

        dir_path = os.path.dirname(full_filename)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        return path

    def save_as_jpg(self, full_filename, msg='', msg_loglevel=logging.INFO):
        path = self._save_as_prep(full_filename, 'jpg', msg, msg_loglevel)
        cv2.imwrite(path, self.get_raw_screenshot(), [cv2.IMWRITE_JPEG_QUALITY, 70])

    def save_as_png(self, full_filename, msg='', msg_loglevel=logging.INFO):
        path = self._save_as_prep(full_filename, 'png', msg, msg_loglevel)
        cv2.imwrite(path, self.get_raw_screenshot())

    def save_in_findfailed(self, format_='jpg', msg='', msg_loglevel=logging.INFO):
        assert format_ in ['png', 'jpg']

        file_name = os.path.join(
            pikuli.Settings.getFindFailedDir(),
            'ManuallyStored-{dt}-{reg}.{format}'.format(
                dt=datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S'),
                reg='({},{},{},{})'.format(self._x, self._y, self._w, self._h),
                format=format_))

        if msg:
            msg += ' ({} has been stored manually)'.format(self)
        else:
            msg = 'Mmanually storing of {}.'.format(self)
        if format_ == 'jpg':
            self.save_as_jpg(file_name, msg=msg, msg_loglevel=msg_loglevel)
        else:
            self.save_as_png(file_name, msg=msg, msg_loglevel=msg_loglevel)

    @property
    def geometry(self):
        return self._x, self._y, self._w, self._h

    def get_raw_screenshot(self):
        """Returns Region screenshot as a 2D numpy array of int8
        """
        return _take_screenshot(*(self.geometry + (self._main_window_hwnd,)))

    def __find(self, ps, field):
        # cv2.imshow('field', field)
        # cv2.imshow('pattern', ps._cv2_pattern)
        # cv2.waitKey(3*1000)
        # cv2.destroyAllWindows()

        CF = 0
        try:
            if CF == 0:
                res = cv2.matchTemplate(field, ps._cv2_pattern, cv2.TM_CCORR_NORMED)
                loc = np.where(res > ps.getSimilarity())  # 0.995
            elif CF == 1:
                res = cv2.matchTemplate(field, ps._cv2_pattern, cv2.TM_SQDIFF_NORMED)
                loc = np.where(res < 1.0 - ps.getSimilarity())  # 0.005
        except cv2.error as ex:
            raise FindFailed('OpenCV ERROR: ' + str(ex), patterns=ps, field=field, cause=FindFailed.OPENCV_ERROR)

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

        #t = time.time()
        #cv2.imwrite('c:\\tmp\\%i-%06i-field.png' % (int(t), (t-int(t))*10**6), field)
        #cv2.imwrite('c:\\tmp\\%i-%06i-pattern.png' % (int(t), (t-int(t))*10**6), ps._cv2_pattern)

        return map(lambda x, y, s: (int(x) + self._x, int(y) + self._y, float(s)), loc[1], loc[0], res[loc[0], loc[1]])


    def findAll(self, ps, delay_before=0):
        '''
        Если ничего не найдено, то вернется пустой list, и исключения FindFailed не возникнет.
        '''
        err_msg_template = '[error] Incorect \'findAll()\' method call:\n\tps = %s\n\ttypeOf ps=%s\n\tdelay_before = %s\n\tadditional comment: %%s' % (str(ps),type(ps), str(delay_before))

        try:
            delay_before = float(delay_before)
        except ValueError:
            raise FailExit(err_msg_template % 'delay_before is not float')

        ps = _get_list_of_patterns(ps, err_msg_template % 'bad \'ps\' argument; it should be a string (path to image file) or \'Pattern\' object')

        time.sleep(delay_before)
        (pts, self._last_match) = ([], [])
        try:
            for p in ps:
                pts.extend( self.__find(p, self.__get_field_for_find()) )
                self._last_match.extend( map(lambda pt: Match(pt[0], pt[1], p._w, p._h, p, pt[2]), pts) )

        except FindFailed as ex:
            dt = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

            fn_field = os.path.join(pikuli.Settings.getFindFailedDir(), 'Region-findAll-field-'   + dt + '-' + '+'.join([Pattern(p).getFilename(full_path=False) for p in ps]) + '.jpg')
            cv2.imwrite(fn_field, ex.field, [cv2.IMWRITE_JPEG_QUALITY, 70])

            fn_pattern = []
            for p in ex.patterns:
                fn_pattern += [os.path.join(pikuli.Settings.getFindFailedDir(), 'Region-findAll-pattern-' + dt + '-' + p.getFilename(full_path=False) + '.jpg')]
                cv2.imwrite(fn_pattern[-1], p.get_image(), [cv2.IMWRITE_JPEG_QUALITY, 70])

            logger.info('pikuli.Region.findAll: FindFailed; ps = {}'
                        '\n\tField stored as:\n\t\t[[f]]'
                        '\n\tPatterns strored as:\n\t\t{}'.format(ps, '\b\t\t'.join(['[[f]]'] * len(fn_pattern))),
                        extra={'f': [File(fn_field)] + [File(f) for f in fn_pattern]})

            raise ex
        else:
            scores = '[' + ', '.join(['%.2f'%m.getScore() for m in self._last_match]) + ']'
            logger.info('pikuli.findAll: total found {} matches of <{}> in {}; scores = {}'.format(
                len(self._last_match), str(ps), str(self), scores))
            return self._last_match


    def _wait_for_appear_or_vanish(self, ps, timeout, aov, exception_on_find_fail=None):
        '''
            ps может быть String или List:
              -- Если ps - это список (list) и aov == 'appear', то возвращается первый найденный элемент. Это можно использвоать, если требуется найти любое из переданных изображений.
              -- Если ps - это список (list) и aov == 'vanish', то функция завершается, когда не будет найден хотя бы один из шаблонов.

            exception_on_find_fail -- необязательный аргумент True|False. Здесь нужен только для кастопизации вывода в лог в случае ненахождения паттерна.
        '''
        ps = _get_list_of_patterns(ps, 'bad \'ps\' argument; it should be a string (path to image file) or \'Pattern\' object: %s' % str(ps))

        if self.w == 0:
            raise FailExit('bad rectangular area: self.w == 0')
        if self.h == 0:
            raise FailExit('bad rectangular area: self.h == 0')

        if timeout is None:
            timeout = self._find_timeout
        else:
            try:
                timeout = float(timeout)
                if timeout < 0:
                    raise ValueError
            except ValueError:
                raise FailExit('bad argument: timeout = \'%s\'' % str(timeout))

        prev_field = None
        elaps_time = 0
        while True:
            field = self.__get_field_for_find()

            if prev_field is None or (prev_field != field).all():
                for _ps_ in ps:
                    pts = self.__find(_ps_, field)
                    if aov == 'appear':
                        if len(pts) != 0:
                            # Что-то нашли. Выберем один вариант с лучшим 'score'. Из несольких с одинаковыми 'score' будет первый при построчном проходе по экрану.
                            pt = max(pts, key=lambda pt: pt[2])
                            logger.info( 'pikuli.%s.<find...>: %s has been found' % (type(self).__name__, _ps_.getFilename(full_path=False)))
                            return Match(pt[0], pt[1], _ps_._w, _ps_._h, _ps_, pt[2])
                    elif aov == 'vanish':
                        if len(pts) == 0:
                            logger.info( 'pikuli.%s.<find...>: %s has vanished' % (type(self).__name__, _ps_.getFilename(full_path=False)))
                            return
                    else:
                        raise FailExit('unknown \'aov\' = \'%s\'' % str(aov))

            time.sleep(DELAY_BETWEEN_CV_ATTEMPT)
            elaps_time += DELAY_BETWEEN_CV_ATTEMPT
            if elaps_time >= timeout:
                logger.info( 'pikuli.%s.<find...>: %s hasn\'t been found' % (type(self).__name__, _ps_.getFilename(full_path=False)) +
                     ', but exception was disabled.' if exception_on_find_fail is not None and not exception_on_find_fail else '' )
                #TODO: Какие-то ту ошибки. Да и следует передавать, наверно, картинки в FindFailed(), а где-то из модулей робота сохранять, если надо.
                #t = time.time()
                #cv2.imwrite(os.path.join(pikuli.Settings.getFindFailedDir, '%i-%06i-pattern.png' % (int(t), (t-int(t))*10**6)), ps[0]._cv2_pattern)
                #cv2.imwrite(os.path.join(pikuli.Settings.getFindFailedDir, '%i-%06i-field.png' % (int(t), (t-int(t))*10**6)), field)

                #t = time.time()
                #cv2.imwrite('d:\\tmp\\%i-%06i-pattern.png' % (int(t), (t-int(t))*10**6), ps[0]._cv2_pattern)
                #cv2.imwrite('d:\\tmp\\%i-%06i-field.png' % (int(t), (t-int(t))*10**6), field)
                #cv2.imwrite('c:\\tmp\\FindFailed-pattern.png', ps[0]._cv2_pattern)
                #cv2.imwrite('c:\\tmp\\FindFailed-field.png', field)

                failedImages = ', '.join(map(lambda p: p.getFilename(full_path=True), ps))
                raise FindFailed(
                    "Unable to find '{}' in {} after {} secs of trying".format(failedImages, self, elaps_time),
                    patterns=ps, field=field
                )


    def find(self, ps, timeout=None, exception_on_find_fail=True, save_img_file_at_fail=None):
        '''
        Ждет, пока паттерн не появится.

        timeout определяет время, в течение которого будет повторяься неудавшийся поиск. Возможные значения:
            timeout = 0     --  однократная проверка
            timeout = None  --  использование дефолтного значения
            timeout = <число секунд>

        Возвращает Region, если паттерн появился. Если нет, то:
            a. исключение FindFailed при exception_on_find_fail = True
            b. возвращает None при exception_on_find_fail = False.

        save_img_file_at_fail  --  Сохранять ли картинки при ошибке поиска: True|False|None. None -- значение берется из exception_on_find_fail.
        '''
        #logger.info('pikuli.find: try to find %s' % str(ps))
        try:
            self._last_match = self._wait_for_appear_or_vanish(ps, timeout, 'appear', exception_on_find_fail=exception_on_find_fail)

        except FailExit:
            self._last_match = None
            raise FailExit('\nNew stage of %s\n[error] Incorect \'find()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))

        except FindFailed as ex:
            if save_img_file_at_fail or save_img_file_at_fail is None and exception_on_find_fail:
                if not isinstance(ps, list):
                    ps = [ps]
                dt = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                #self.save_as_jpg(os.path.join(pikuli.Settings.getFindFailedDir(), 'Region-find-' + dt + '_' + '+'.join([Pattern(p).getFilename(full_path=False) for p in ps]) + '.jpg'))

                fn_field   = os.path.join(pikuli.Settings.getFindFailedDir(), 'Region-find-field-'   + dt + '-' + '+'.join([Pattern(p).getFilename(full_path=False) for p in ps]) + '.jpg')
                cv2.imwrite(fn_field, ex.field, [cv2.IMWRITE_JPEG_QUALITY, 70])

                fn_pattern = []
                for p in ex.patterns:
                    fn_pattern += [os.path.join(pikuli.Settings.getFindFailedDir(), 'Region-find-pattern-' + dt + '-' + p.getFilename(full_path=False) + '.jpg')]
                    cv2.imwrite(fn_pattern[-1], p.get_image(), [cv2.IMWRITE_JPEG_QUALITY, 70])

                logger.info('pikuli.Region.find: FindFailed; ps = {}'
                            '\n\tField stored as:\n\t\t[[f]]'
                            '\n\tPatterns strored as:\n\t\t{}'.format(ps, '\b\t\t'.join(['[[f]]'] * len(fn_pattern))),
                            extra={'f': [File(fn_field)] + [File(f) for f in fn_pattern]})

            else:
                logger.info('pikuli.Region.find: FindFailed; exception_on_find_fail = %s; ps = %s' % (str(exception_on_find_fail), str(ps)))

            if exception_on_find_fail or ex.cause != FindFailed.NOT_FOUND_ERROR:
                raise ex
            else:
                return None

        else:
            return self._last_match

    def waitVanish(self, ps, timeout=None):
        ''' Ждет, пока паттерн не исчезнет. Если паттерна уже не было к началу выполнения процедуры, то завершается успешно.
        timeout может быть положительным числом или None. timeout = 0 означает однократную проверку; None -- использование дефолтного значения.'''
        try:
            self._wait_for_appear_or_vanish(ps, timeout, 'vanish')
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'waitVanish()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
        except FindFailed:
            logger.info(str(ps))
            return False
        else:
            return True
        finally:
            self._last_match = None


    def exists(self, ps):
        self._last_match = None
        try:
            self._last_match = self._wait_for_appear_or_vanish(ps, 0, 'appear')
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'exists()\' method call:\n\tself = %s\n\tps = %s' % (traceback.format_exc(), str(self), str(ps)))
        except FindFailed:
            logger.info(str(ps))
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
                self._last_match = self._wait_for_appear_or_vanish(ps, timeout, 'appear')
            except FailExit:
                self._last_match = None
                raise FailExit('\nNew stage of %s\n[error] Incorect \'wait()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
            else:
                return self._last_match


    def getLastMatch(self):
        ''' Возвращает результаты последнего поиска. '''
        if self._last_match is None or self._last_match == []:
            raise FindFailed('getLastMatch() is empty')
        return self._last_match


    def set_find_timeout(self, timeout):
        if timeout is None:
            self._find_timeout = DEFAULT_FIND_TIMEOUT
        else:
            self._find_timeout = verify_timeout_argument(timeout, err_msg='[error] Incorect Region.set_find_timeout() method call')

    def get_find_timeout(self):
        return self._find_timeout

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
        self.center.type(text,
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

    def find_all_solid_markers_by_piece(self, ps):
        '''
        Ищет все почти solid-color маркеры. Выделяется группа найденных как один маркер --
        это нужно, т.к. шаблон ненмого меньше маркера в картинке и поэтому поиск находит несолько
        в почти одном и том же месте

        Алгоритм: все найденные перекрывающиеся маркеры одного вида -- это один маркер. Его центр --
        это среднее между центрами всех найденных "фантомов". Если два маркера не перекрываются
        между собой, но оба перекрываются с третьтим -- всех троих группируем в один.

        Если ничего не найдено, то возвращается пустой список.
        '''

        if not isinstance(ps, list):
            ps = [ps]

        matches = []  # Список списков. В него будут помещаться
        for p in ps:
            unsorted_matches = self.findAll(p)  # Несгруппированные вхождения шаблона
            grouped_matches = []
            while len(unsorted_matches) > 0:
                next_match = unsorted_matches.pop(0)

                # Добавим next_match в существующую гурппу ...
                logger.info(grouped_matches)
                for g in grouped_matches:
                    for m in g:
                        if abs(m.x - next_match.x) < next_match.w and \
                           abs(m.y - next_match.y) < next_match.h:
                            g.append(next_match)
                            next_match = None
                            break
                    if next_match is None:
                        break

                # ... или созданим для него новую группу.
                if next_match is not None:
                    grouped_matches.append([next_match])

            matches.extend(grouped_matches)

        # Замени группы совпадений на итоговые классы Match:
        for i in range(len(matches)):
            sum_score = sum( [m.getScore() for m in matches[i]] )
            x = sum( [m.x*m.getScore() for m in matches[i]] ) / sum_score
            y = sum( [m.y*m.getScore() for m in matches[i]] ) / sum_score
            matches[i] = Match(x, y, matches[i][0].w, matches[i][0].h, matches[i][0].getPattern(), sum_score/len(matches[i]))

        return matches

