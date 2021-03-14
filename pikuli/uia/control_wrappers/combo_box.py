# -*- coding: utf-8 -*-

from pikuli import FindFailed, wait_while_not

from . import CONTROL_CHECK_TIMEOUT
from .uia_control import UIAControl
from .mixin import _ValuePattern_methods, _Enter_Text_method


class ComboBox(UIAControl, _ValuePattern_methods, _Enter_Text_method):

    """
    Методы:
        select_item    --  Мышкой выбирает элемент из выпадающего меню.
        set_value_api  --  Через UIA API выставить новое значение (метод из _ValuePattern_methods).
        get_value      --  Переопредеялем метод из _ValuePattern_methods.
    """

    CONTROL_TYPE = 'ComboBox'
    REQUIRED_PATTERNS = {}

    def list_items(self):
        '''
            Если меню открыто, то вренут списко объектов, описывающих каждый пункт меню (теоретически, это может быть пустой список).
            Если меню закрыто, то вернет None.
        '''
        l = self.find(ControlType='List', exact_level=1, exception_on_find_fail=False, timeout=1)
        if l is None:
            return None
        return l.list_items()

    """def name_of_choosed(self):  --  есть метод _ValuePattern_methods.get_value()
        ''' Вернет тектсовую строку того пукта выпдающего меню, который выбран. '''
        return self.find(ControlType='Text', exact_level=1).get_value()"""

    def get_item_by_name(self, item_name):
        """
        Если список ракрыт, то вернут подходящий объект ListItem. Если объекта не нашлось в списке в течение timeout, то будет исключение
        :param item_name: название поля
        """
        item_name = str(item_name)
        if self.list_items() is None:
            raise FindFailed('List of ComboBox %s was not found. Is this list collapsed?' % repr(self))
        if wait_while_not(lambda: any(item_name in str(s) for s in self.list_items()), CONTROL_CHECK_TIMEOUT):
            items = [i for i in self.list_items() if i.Name == item_name]
            assert len(items) == 1  # Не меньше и не больше одного
            return items[0]
        else:
            raise FindFailed('ComboBox item was not show for timeout {}'.format(CONTROL_CHECK_TIMEOUT))

    def select_item(self, item_name):
        """
        Выбрать пункт.
            item_name  --  строка, содержащая текст делаемого пункта выпалдающего меню.
        """
        item_name = str(item_name)
        if self.get_value() != item_name:
            if self.list_items() is None:
                self.click()
            self.get_item_by_name(item_name).click()

    def get_value(self):
        '''
        У нас комбобоксы бывают следующих типов:
            <text> + <Open button>
            <edit> + <Open button>
            <edit> + <spiner>
        Может сложиться ситуация, когда Value всего комбобокса пустое, а Value у <edit> -- нет. И как раз этот дочерний объект и содержит искомые данные.

        Переопределяем функцию из _ValuePattern_methods. Делаем так:
            -- если value_cmbbox == '', то возвращаем value_child
            -- если value_cmbbox == value_child, то возвращаем это
            -- если value_cmbbox != value_child и value_cmbbox != '', то генерируем исключение
        '''
        value_cmbbox = self.get_pattern('ValuePattern').CurrentValue or None

        childs = self.find_all(ControlType='Text', exact_level=1) + self.find_all(ControlType='Edit', exact_level=1)
        if len(childs) > 1:
            raise Exception('ComboBox.get_value(...): there are more than one \'Text\' or/and \'Edit\' child controls:\n\tchilds = %s' % str(childs))
        value_child = childs[0].get_value()

        # Есть сам комбо-бокс, а есть его дочерний объект. Бывает, что комбо-бокс возрвращает путоту -- тогда данные надо брыть у дочернего объекта.
        # Комбобокс, теоретически, может и пустую строку возвращать.
        if value_cmbbox is None  or  value_cmbbox == '' and value_child != '':
            return value_child
        elif value_cmbbox != value_child:
            raise Exception('ComboBox.get_value(...): values of ComboBox-self and its child Text or Edit object differ:\n\tvalue_cmbbox = %s\n\tvalue_child = %s' % (value_cmbbox, value_child))
        else:
            return value_cmbbox
