from .uia_control import UIAControl


class TabItem(UIAControl):

    CONTROL_TYPE = 'TabItem'

    def is_selected(self):
        return bool(self.get_pattern('SelectionItemPattern').CurrentIsSelected)
