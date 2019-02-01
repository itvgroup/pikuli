# -*- coding: utf-8 -*-

from .adapter import Adapter
from .identifer_names import element_property_names, control_type_names
from .patterns_plain_description import patterns_plain_description


class IdNameMap(object):

    def __init__(self, map_builder, names):
        self._name2id = map_builder(names)
        self._id2name = {v: k for k, v in self._name2id.items()}

    def name2id(self, name):
        return self._name2id[name]

    def try_name2id(self, name):
        return self._name2id.get(name, None)

    def try_id2name(self, id_):
        return self._id2nam.get(id_, None)

    def items(self):
        for name, id_ in self._name2id.items():
            yield name, id_

    def names(self):
        return self._name2id.keys()


element_properties_map = IdNameMap(Adapter.build_properties_map, element_property_names)

properties_of_pattern_availability_map = IdNameMap(
    Adapter.build_properties_map,
    ["Is{pattern_name}Available".format(pattern_name=n) for n in patterns_plain_description])

def get_property_id(name):
    id_ = (element_properties_map.try_name2id(name) or
           properties_of_pattern_availability_map.try_name2id(name))
    if id_ is None:
        raise Exception("Property '{}' is no available".format(name))
    return id_


control_type_map = IdNameMap(Adapter.build_control_types_map, control_type_names)

def get_control_type_id(name):
    id_ = try_get_control_type_id(name)
    if id_ is None:
        raise Exception("Control Type '{}' is no available".format(name))
    return id_

def try_get_control_type_id(name):
    return control_type_map.try_name2id(name)

def get_control_type_name(id_):
    name = control_type_map.try_id2name(id_)
    if name is None:
        raise Exception("Control Type id '{}' is no available".format(id_))
    return name


patterns_map = IdNameMap(Adapter.build_patterns_map, patterns_plain_description.keys())

def get_pattern_id(name):
    id_ = try_get_pattern_id(name)
    if id_ is None:
        raise Exception("Pattern '{}' is no available".format(name))
    return id_

def try_get_pattern_id(name):
    return patterns_map.try_name2id(name)
