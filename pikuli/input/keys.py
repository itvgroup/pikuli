# -*- coding: utf-8 -*-

from enum import Enum, EnumMeta

from .platform_init import KeyCode, ScrollDirection


class InputSequence(object):

    def __init__(self, obj):
        if obj is None:
            self._container = []
        elif isinstance(obj, InputSequence):
            self._container = list(obj._container)
        elif isinstance(obj, (Key, KeyModifier)):
            self._container = [obj]
        else:
            self._container = [unicode(obj)]

    def __add__(self, right_operand):
        right_operand = InputSequence(right_operand)
        return InputSequence._join(self, right_operand)

    def __radd__(self, left_operand):
        left_operand = InputSequence(left_operand)
        return InputSequence._join(left_operand, self)

    @classmethod
    def _join(self, c1, c2):
        c = InputSequence(c1)
        c._container.extend(c2._container)
        return c

    def __str__(self):
        return "<InputSequence:{!s}>".format(self._container)

    def __repr__(self):
        return "<InputSequence:{!r}>".format(self._container)

    def _is_consist_of(self, elem_type):
        return all([isinstance(e, elem_type) for e in self._container])

    def _is_all_unique(self):
        return len(set(self._container)) == len(self._container)

    def __iter__(self):
        for elem in self._container:
            if isinstance(elem, basestring):
                for c in elem:
                    yield c
            else:
                yield elem


class KeyMeta(EnumMeta):
    def __new__(mcls, name, bases, dct):
        dct.update({e.name: e.value for e in list(KeyCode)})
        return super(KeyMeta, mcls).__new__(mcls, name, bases, dct)


class KeyBaseEnum(int, Enum):

    @property
    def key_code(self):
        return int(self.value)

    def __add__(self, right_operand):
        right_operand = InputSequence(right_operand)
        return InputSequence(self) + right_operand

    def __radd__(self, left_operand):
        left_operand = InputSequence(left_operand)
        return left_operand + InputSequence(self)


class Key(KeyBaseEnum):
    '''
    Коды специальных клавиш. Позволяют легко добавлять их к строкам в коде. К примеру:
        type_text("some text" + Key.ENTER)

    Код клавиши зависит от OS. Для Windows это Virtual-key Code, а в Linux -- коды evdev.
    '''

    __metaclass__ = KeyMeta


class KeyModifier(KeyBaseEnum):
    '''
    Аргумент modifiers функции type_text().
    '''
    ALT   = Key.ALT.value
    CTRL  = Key.CTRL.value
    SHIFT = Key.SHIFT.value

    def __add__(self, right_operand):
        return self._add(right_operand)

    def __radd__(self, left_operand):
        return self._add(left_operand)

    def _add(self, operand):
        self._check_operand_type_is_valid(operand)
        sequence = super(KeyModifier, self).__radd__(operand)
        self._check_result_is_valid(sequence)
        return sequence

    @classmethod
    def _check_operand_type_is_valid(cls, operand):
        is_keymod = isinstance(operand, KeyModifier)
        is_sequence = isinstance(operand, InputSequence)
        is_valid = is_keymod or (is_sequence and operand._is_consist_of(KeyModifier))
        if not is_valid:
            raise TypeError('Operand {!r} ({}) must be {}'.format(operand, type(operand), cls.__name__))

    @classmethod
    def _check_result_is_valid(cls, sequence):
        if not sequence._is_all_unique():
            raise ValueError('Now {} sequence constains duplicates: {!r}'.format(cls.__name__, sequence))
