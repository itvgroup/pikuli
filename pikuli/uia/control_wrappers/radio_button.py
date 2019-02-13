from .uia_control import UIAControl


class RadioButton(UIAControl):

    CONTROL_TYPE = 'RadioButton'

    def is_checked(self):
        return bool(self.get_pattern('SelectionItemPattern').CurrentIsSelected)

    def is_unchecked(self):
        return not self.is_checked()