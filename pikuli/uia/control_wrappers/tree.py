# -*- coding: utf-8 -*-

import re

from pikuli import logger

from .uia_control import UIAControl


class Tree(UIAControl):

    CONTROL_TYPE = 'Tree'
    REQUIRED_PATTERNS = {} # {'SelectionPattern': []}

    def __init__(self, *args, **kwargs):
        super(Tree, self).__init__(*args, **kwargs)
        self._last_tree = []

    def get_current_tree(self):
        ''' Дерево вида:
        [
            (<TreeItem>, [
                <TreeItem>, [...],  # если узел развернут (включая частичное разворачивание)
                <TreeItem>, [],     # если узел полностью свернут
                <TreeItem>, None    # если нет дочерних узелков
            ]),
            (<TreeItem>, []),
            (<TreeItem>, None),
            ...
        ]
        Если дерево пусто, то вернется None (не пустой список []).
        '''

        def _next_node(treeitem):
            if not treeitem.is_expandable():
                # Если нет ветви, идущей из этого "узелка":
                branch = None
            else:
                # Если есть такая ветвь:
                childs = treeitem.find_all(exact_level=1)
                branch = map(_next_node, childs)
            return (treeitem, branch)

        self._last_tree = []
        for treeitem in self.find_all(exact_level=1):
            self._last_tree.append(_next_node(treeitem))

        return self._last_tree

    """def get_first_item(self):
        return self.find(exact_level=1)"""

    def list_current_subitems(self):
        ''' Вернут список дочерних узелков (1 уровень вложенности). Вернет None, если нет дочерних узелков. '''
        items = self.find_all(exact_level=1, ControlType='TreeItem')
        if len(items) == 0:
            return None
        return items

    def find_item(self, item_name, force_expand=False, timeout=None, exception_on_find_fail=True):
        '''
            item_name -- Cписок строк-названий эелементов дерева, пречисленных по их вложенности один в другой. Последняя строка в списке -- искомый элемент.
            force_expand -- разворачивать ли свернутые элементы на пути поиска искового.
        '''
        # logger.debug(CONSOLE_ERASE_LINE_SEQUENCE)
        logger.debug('pikuli.Tree.find_item: searching by criteria item_name = \'%s\', timeout = %s' % (str(item_name), str(timeout)))

        if isinstance(item_name, (str, re.Pattern)):
            item_name = [item_name]
        if not isinstance(item_name, (list, tuple)):
            raise Exception('pikuli.ui_element.Tree: not isinstance(item_name, list) and not isinstance(item_name, str)\n\titem_name = %s\n\ttimeout = %s' % (str(item_name), str(timeout)))

        if len(item_name) == 0:
            raise Exception('pikuli.ui_element.Tree: len(item_name) == 0')
        else:
            elem = self.find(Name=item_name[0], exact_level=1, ControlType='TreeItem', timeout=timeout, exception_on_find_fail=exception_on_find_fail)
            if elem is None:
                logger.debug('pikuli.ui_element.Tree.find_item: %s has not been found. No exception -- returning None' % str(item_name))
                return None
            if len(item_name) == 1:
                found_elem = elem
            else:
                found_elem = elem.find_item(item_name[1:], force_expand, timeout=timeout, exception_on_find_fail=exception_on_find_fail)

        """
        TODO: не работает пауза: сразу содает несолкьо анализов ситацайии, не дожидаясь появления первого
        else:
            elem = self.find_all(Name=item_name[0], exact_level=1, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
            if (elem is None) or (len(elem) == 0):
                if exception_on_find_fail:
                    logger.error('pikuli.ui_element.Tree.find_item: \'%s\' has not been found. Raising exception...' % str(item_name))
                    raise Exception('pikuli.ui_element.Tree.find_item: \'%s\' has not been found.' % str(item_name))
                else:
                    logger.error('pikuli.ui_element.Tree.find_item: \'%s\' has not been found. No exception -- returning None' % str(item_name))
                    return None
            if len(elem) != 1:
                if exception_on_find_fail:
                    logger.error('pikuli.ui_element.Tree.find_item: more than one elemnt \'%s\' has been found. Raising exception...' % str(item_name))
                    raise Exception('pikuli.ui_element.Tree: more than one elemnt \'%s\' has been found.' % str(item_name))
                else:
                    logger.error('pikuli.ui_element.Tree.find_item: more than one elemnt \'%s\' has been found. No exception -- returning None' % str(item_name))
                    return None

            if len(item_name) == 1:
                found_elem = elem[0]
            else:
                found_elem = elem[0].find_item(item_name[1:], force_expand, timeout=timeout, exception_on_find_fail=exception_on_find_fail)
        """

        return found_elem
