# -*- coding: utf-8 -*-

from enum import Enum, EnumMeta


class ApiEnumAutoval(Enum):

    def __new__(cls, default_val):
        obj = object.__new__(cls)
        obj._value_ = len(cls.__members__)
        return obj

    @property
    def _c_name(self):
        return self.name


class ApiEnumExplicit(int, Enum):

    @property
    def _c_name(self):
        """
        Python disallow to use some identifiers as enum field (`None` for example).
        This method translate pythonic names to C-style API.
        In case of API's name `None` it means the `None_` as pythonic editon.
        """
        name = self.name if self.name != 'None_' else 'None'
        return name


class Enums(object):

    def _add(self, enum):
        if not self.is_enum(enum):
            raise Exception('{} is not Enum'.format(enum))
        setattr(self, enum.__name__, enum)

    def get_collection(self):
        return {n: e for n, e in self.__dict__.items() if Enums.is_enum(e)}

    @classmethod
    def is_enum(cls, obj):
        return isinstance(obj, EnumMeta)

    def __str__(self):
        return str(self.get_collection().keys())


class IdNameMap(object):

    def __init__(self, map_builder, names):
        self._name2id = map_builder(names)
        self._id2name = {v: k for k, v in self._name2id.items()}

    def name2id(self, name):
        return self._name2id[name]

    def try_name2id(self, name):
        return self._name2id.get(name, None)

    def try_id2name(self, id_):
        return self._id2name.get(id_, None)

    def items(self):
        for name, id_ in self._name2id.items():
            yield name, id_

    def names(self):
        return self._name2id.keys()

    def ids(self):
        return self._name2id.values()
