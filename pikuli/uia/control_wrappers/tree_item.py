# -*- coding: utf-8 -*-
import time

from pikuli import logger, FindFailed
from pikuli.uia.adapter import Enums

from .uia_control import UIAControl
from .check_box import CheckBox


class TreeItem(CheckBox, UIAControl):
    """
    Наследование от :class:`CheckBox` здесь чисто утилитарное -- нужные его методы.
    """

    CONTROL_TYPE = 'TreeItem'
    REQUIRED_PATTERNS = {
        'SelectionItemPattern': ['is_selected'],
        'ExpandCollapsePattern': ['is_expandable', 'is_expanded', 'is_collapsed', 'expand', 'collapse'],
        'ScrollItemPattern': ['scroll_into_view'],
        'TogglePattern': ['is_unchecked', 'is_checked', 'uncheck', 'check', 'check_or_uncheck']
    }

    def is_selected(self):
        return bool(self.get_pattern('SelectionItemPattern').CurrentIsSelected)

    def is_expandable(self):
        return not (self.get_pattern('ExpandCollapsePattern').CurrentExpandCollapseState == Enums.ExpandCollapseState.LeafNode)

    def select(self):
        # self.get_pattern('SelectionItemPattern').AddToSelection()
        self.get_pattern('SelectionItemPattern').Select()

    def unselect(self):
        try:
            self.get_pattern('SelectionItemPattern').RemoveFromSelection()
            assert not self.is_selected()
        except Exception as ex:
            logger.exception(ex)

    def is_expanded(self):
        ''' Проверка, что развернут текущий узел (полностью, не частично). Без учета состояния дочерних узлов. Если нет дочерних, то функция вернет False. '''
        if not self.is_expandable():
            return False
        return (self.get_pattern('ExpandCollapsePattern').CurrentExpandCollapseState == Enums.ExpandCollapseState.Expanded)

    def is_collapsed(self):
        ''' Проверка, что развернут текущий узел (полностью, не частично). Без учета состояния дочерних узлов. Если нет дочерних, то функция вернет True. '''
        if not self.is_expandable():
            return True
        return (self.get_pattern('ExpandCollapsePattern').CurrentExpandCollapseState == Enums.ExpandCollapseState.Collapsed)

    def expand(self):
        if self.is_expandable() and not self.is_expanded():
            self.get_pattern('ExpandCollapsePattern').Expand()

    def collapse(self):
        if self.is_expandable() and not self.is_collapsed():
            self.get_pattern('ExpandCollapsePattern').Collapse()
        if not self.is_collapsed():
            raise Exception('pikuli.ui_element: can not collapse TreeItem \'%s\'' % self.Name)

    def scroll_into_view(self):
        self.get_pattern('ScrollItemPattern').ScrollIntoView()

    def list_current_subitems(self, force_expand=False):
        ''' Вернут список дочерних узелков (1 уровень вложенности), если текущий узел развернут. Вернет [], если узел свернут полностью или частично. Вернет None, если нет дочерних узелков. '''
        if not self.is_expandable():
            return None
        if not self.is_expanded():
            if force_expand:
                self.expand()
            else:
                logger.warning('Node {} is collapsed, but force_expand = {}'.format(self, force_expand))
        if self.is_expanded():
            return self.find_all(ControlType='TreeItem', exact_level=1)
        return []

    def find_item(self, item_name, force_expand=False, timeout=None, exception_on_find_fail=True):
        '''
            item_name -- Cписок строк-названий эелементов дерева, пречисленных по их вложенности один в другой. Последняя строка в списке -- искомый элемент.
            force_expand -- разворачивать ли свернутые элементы на пути поиска искового.
        '''
        # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
        logger.debug('pikuli.TreeItem.find_item: searching by criteria item_name = \'%s\', timeout = %s' % (str(item_name), str(timeout)))

        if not isinstance(item_name, (list, tuple)):
            item_name = [item_name]
        if len(item_name) == 0:
            raise Exception('pikuli.ui_element.TreeItem: len(item_name) == 0')
        if not self.is_expanded() and not force_expand:
            raise FindFailed('pikuli.ui_element.TreeItem: item \'%s\' was found, but it is not fully expanded. Try to set force_expand = True.\nSearch arguments:\n\titem_name = %s\n\tforce_expand = %s' % (self.Name, str(item_name), str(force_expand)))

        self.expand()

        elem = self.find(Name=item_name[0], ControlType='TreeItem', exact_level=1, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
        if elem is None:
            logger.debug('pikuli.ui_element.TreeItem.find_item: %s has not been found. No exception -- returning None' % str(item_name))
            return None
        if len(item_name) == 1:
            found_elem = elem
        else:
            found_elem = elem.find_item(item_name[1:], force_expand, timeout=timeout, exception_on_find_fail=exception_on_find_fail)

        """
        TODO: не работает пауза: сразу содает несолкьо анализов ситацайии, не дожидаясь появления первого
        elem = self.find_all(Name=item_name[0], exact_level=1, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
        if (elem is None) or (len(elem) == 0):
            if exception_on_find_fail:
                logger.error('pikuli.ui_element.TreeItem.find_item: \'%s\' has not been found. Raising exception...' % str(item_name))
                raise Exception('pikuli.ui_element.TreeItem.find_item: \'%s\' has not been found.' % str(item_name))
            else:
                logger.error('pikuli.ui_element.TreeItem.find_item: \'%s\' has not been found. No exception -- returning None' % str(item_name))
                return None
        if len(elem) != 1:
            if exception_on_find_fail:
                logger.error('pikuli.ui_element.TreeItem.find_item: more than one elemnt \'%s\' has been found. Raising exception...' % str(item_name))
                raise Exception('pikuli.ui_element.TreeItem: more than one elemnt \'%s\' has been found.' % str(item_name))
            else:
                logger.error('pikuli.ui_element.TreeItem.find_item: more than one elemnt \'%s\' has been found. No exception -- returning None' % str(item_name))
                return None

        if len(item_name) == 1:
            found_elem = elem[0]
        else:
            found_elem = elem[0].find_item(item_name[1:], force_expand, timeout=timeout)
        """

        return found_elem
