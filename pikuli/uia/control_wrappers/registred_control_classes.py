# -*- coding: utf-8 -*-

import importlib
import numbers

from ..adapter.oleacc_h import ROLE_SYSTEM, ROLE_SYSTEM_rev


class RegisteredControlClasses:
    """
    TODO: Improme registration machinery and criteria structure.
    """

    _by_class_name = {}
    _by_control_type = {}
    _by_legacy_role = {}

    @classmethod
    def _register_all(cls):
        to_be_registered = [
            (".button", "Button"),
            (".check_box", "CheckBox"),
            (".combo_box", "ComboBox"),
            (".custom_control", "CustomControl"),
            # (".desktop", "Desktop"), - exclude this one due to it hasn't CONTROL_TYPE
            (".data_grid", "DataGrid"),
            (".data_item", "DataItem"),
            (".document", "Document"),
            (".edit", "Edit"),
            (".group", "Group"),
            (".header", "Header"),
            (".header_item", "HeaderItem"),
            (".hyperlink", "Hyperlink"),
            (".image", "Image"),
            (".list", "List"),
            (".list_item", "ListItem"),
            (".menu", "Menu"),
            (".menu_bar", "MenuBar"),
            (".menu_item", "MenuItem"),
            (".pane", "Pane"),
            (".progress_bar", "ProgressBar"),
            (".property_grid", "ANPropGrid_Table"),
            (".radio_button", "RadioButton"),
            (".scroll_bar", "ScrollBar"),
            (".separator", "Separator"),
            (".split_button", "SplitButton"),
            (".spinner", "Spinner"),
            (".status_bar", "StatusBar"),
            (".tab", "Tab"),
            (".tab_item", "TabItem"),
            (".text", "Text"),
            (".thumb", "Thumb"),
            (".title_bar", "TitleBar"),
            (".tool_bar", "ToolBar"),
            (".tree", "Tree"),
            (".tree_item", "TreeItem"),
            (".window", "Window"),
        ]

        for module_loc, class_name in to_be_registered:
            module = importlib.import_module(module_loc, package="pikuli.uia.control_wrappers")
            constrol_class = getattr(module, class_name)
            #if not RegisteredControlClasses.try_get_class_by_control_type(control_cls.CONTROL_TYPE):
            RegisteredControlClasses._add_new(class_name, constrol_class)

    @classmethod
    def _add_new(cls, name, new_class):
        control_type = new_class.CONTROL_TYPE
        legacyacc_role = getattr(new_class, 'LEGACYACC_ROLE', None)

        if name in cls._by_class_name:
            raise Exception("{!r} has been already added".format(name))
        if control_type in cls._by_control_type:
            raise Exception("{!r} with CONTROL_TYPE={!r} has been already added".format(name, control_type))
        if legacyacc_role and (legacyacc_role not in ROLE_SYSTEM):
            raise Exception("{!r} with unknown LEGACYACC_ROLE={!r}".format(name, legacyacc_role))

        cls._by_class_name[name] = new_class
        cls._by_control_type[control_type] = new_class
        if legacyacc_role:
            cls._by_legacy_role[legacyacc_role] = new_class

    @classmethod
    def is_class_registred(cls, control_class):
        return control_class in cls._by_class_name.values()

    @classmethod
    def get_class_by_control_type(cls, control_type):
        return cls._by_control_type[control_type]

    @classmethod
    def try_get_class_by_control_type(cls, control_type):
        return cls._by_control_type.get(control_type, None)

    @classmethod
    def try_get_by_legacy_role(cls, legacy_role):
        if isinstance(legacy_role, numbers.Number):
            legacy_role = ROLE_SYSTEM_rev.get(legacy_role, None)
        return cls._by_legacy_role.get(legacy_role, None)
