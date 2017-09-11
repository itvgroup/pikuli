# -*- coding: utf-8 -*-

from math import sqrt


class Vector(object):

    def __init__(self, *args):
        """
        Координаты -- вещественые числа. Или :class:`Vector`.
        """
        if len(args) == 2:
            self._x = float(args[0])
            self._y = float(args[1])
        elif len(args) == 1 and isinstance(args[0], Vector):
            self._x = float(args[0]._x)
            self._y = float(args[0]._y)
        elif len(args) == 1 and isinstance(args[0], (list, tuple)):
            self._x = float(args[0][0])
            self._y = float(args[0][1])
        else:
            raise Exception('{}'.format(args))

    def __add__(self, other):
        """
        Сложение двух векторов
        """
        assert isinstance(other, Vector)
        return Vector(self._x + other._x, self._y + other._y)

    def __sub__(self, other):
        """
        Разность двух векторов
        """
        assert isinstance(other, Vector)
        return Vector(self._x - other._x, self._y - other._y)

    def __mul__(self, other):
        """
        Скалярное произведение двух векторов или умножение на скаляр.
        Скаляр приводится к `float`.
        """
        if isinstance(other, Vector):
            return float(self._x * other._x + self._y * other._y)
        else:
            other = float(other)
            return Vector(self._x * other, self._y * other)

    def __div__(self, other):
        """
        Деление на скаляр. Скаляр приводится к `float`.
        """
        if isinstance(other, Vector):
            raise Exception('Vector division is unsupported')
        else:
            other = float(other)
            return Vector(self._x / other, self._y / other)

    def __floordiv__(self, other):
        """
        Синоним :func:`Vector.__div__`
        """
        return self.__dev__(other)

    def __neg__(self):
        return Vector(-self._x, -self._y)

    def __pos__(self):
        return Vector(self._x, self._y)

    def __abs__(self):
        """
        Модуль вектора.
        """
        return sqrt(self * self)

    def hprod(self, other):
        """
        Произведение Адамара
        """
        return Vector(self._x * other._x, self._y * other._y)

    @property
    def hinv(self):
        """
        Hadamard inverse vector
        """
        return Vector(1.0 / self._x, 1.0 / self._y)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def __repr__(self):
        return '{}({}, {})'.format(self.__class__.__name__, self.x, self.y)

    def __getitem__(self, key):
        """
        Возвращается именно "self.x" и "self.y", как это определяют property-методы экземпляров
        класса.
        """
        if key not in [0, 1]:
            raise IndexError('index "{}" is out of set {0, 1}'.format(key))
        if key:
            return self.y
        else:
            return self.x

    def __iter__(self):
        """
        Возвращается именно "self.x" и "self.y", как это определяют property-методы экземпляров
        класса.
        """
        def targer():
            yield self.x
            yield self.y
        return targer()
