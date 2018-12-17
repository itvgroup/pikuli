# -*- coding: utf-8 -*-

import importlib
import numbers

from pikuli.utils import class_property
from ..adapter.oleacc_h import ROLE_SYSTEM, ROLE_SYSTEM_rev

class RegistredControlClasses(object):

    _by_class_name = {}
    _by_control_type = {}
    _by_legacy_role = {}

    @classmethod
    def _register_all(cls):
        modules = [
            ".button",
            ".check_box",
            ".combo_box",
            ".custom_control",
            ".desktop",
            ".edit",
            ".item",
            ".list",
            ".list_item",
            ".menu",
            ".menu_item",
            ".pane",
            ".property_grid",
            ".text",
            ".tree",
            ".tree_item",
            ".window",
        ]
        for m in modules:
            importlib.import_module(m, package="pikuli.uia.control_wrappers")

    @classmethod
    def _add_new(cls, name, new_class):
        if name in cls._by_class_name:
            raise Exception("{!r} has been already added".format(name))
        if new_class.CONTROL_TYPE in cls._by_control_type:
            raise Exception("{!r} with CONTROL_TYPE={!r} has been already added".format(name, new_class.CONTROL_TYPE))
        if new_class.LEGACYACC_ROLE and (new_class.LEGACYACC_ROLE not in ROLE_SYSTEM):
            raise Exception("{!r} with unknown LEGACYACC_ROLE={!r}".format(name, new_class.LEGACYACC_ROLE))

        cls._by_class_name[name] = new_class
        cls._by_control_type[new_class.CONTROL_TYPE] = new_class
        if new_class.LEGACYACC_ROLE:
            cls._by_legacy_role[new_class.LEGACYACC_ROLE] = new_class

    @classmethod
    def is_class_registred(cls, control_class):
        return control_class in cls._by_class_name.values()

    @classmethod
    def get_class_by_control_type(cls, control_type):
        return cls._by_control_type[control_type]

    @classmethod
    def try_get_by_legacy_role(cls, legacy_role):
        if isinstance(legacy_role, numbers.Number):
            legacy_role = ROLE_SYSTEM_rev.get(legacy_role, None)
        return cls._by_legacy_role.get(legacy_role, None)


class RegistredControlMeta(type):

    def __new__(mcls, name, bases, dct):
        control_cls = super(RegistredControlMeta, mcls).__new__(mcls, name, bases, dct)
        RegistredControlClasses._add_new(name, control_cls)
        return control_cls
