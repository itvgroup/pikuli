# -*- coding: utf-8 -*-
from pikuli import FindFailed, logger
from pikuli.uia.control_wrappers.data_item import DataItem
from .uia_control import UIAControl


class DataGrid(UIAControl):

    CONTROL_TYPE = 'DataGrid'

    def __init__(self, *args, **kwargs):
        super(DataGrid, self).__init__(*args, **kwargs)
        self._last_tree = []

    def find_row(self, row_name, force_expand=False):
        ''' Если row_name:
            a) str или unicode, то это просто имя строки таблицы
            б) если список, то в нем перечислены вложения строк таблицы. Последняя в списке -- искомая строка.

            force_expand -- разворачивать ли свернутые строки, если они обнаружены при поиске строки и являются для нее группирующими.
        '''
        def _find_row_precisely(obj, nested_name, exact_level):
            rows = [DataItem(e) for e in obj.find_all(Name=nested_name, exact_level=exact_level) if e.CONTROL_TYPE in ["DataItem"]]
            if len(rows) > 1:
                Exception('ANPropGrid_Table.find_row._find_row_precisely(...): len(rows) != 0\n\tlen(rows) = %i\n\trows = %s' % (len(rows), str(rows)))
            elif len(rows) == 0:
                raise FindFailed('pikuli.ANPropGrid_Table: row \'%s\' not found.\nSearch arguments:\n\trow_name = %s\n\tforce_expand = %s' % (str(nested_name), str(row_name), str(force_expand)))
            return rows[0]

        logger.debug('pikuli.ANPropGrid_Table.find_row: searching by criteria item_name = \'%s\'' % str(row_name))
        if isinstance(row_name, list):
            row = _find_row_precisely(self, row_name[0], 1)
            for nested_name in row_name[1:]:
                if not row.is_expanded() and not force_expand:
                    raise FindFailed('pikuli.ANPropGrid_Table: row \'%s\' was found, but it is collapsed. Try to set force_expand = True.\nSearch arguments:\n\trow_name = %s\n\tforce_expand = %s' % (str(nested_name), str(row_name), str(force_expand)))
                row.expand()
                row = _find_row_precisely(self, row_name[0], 1)
                row = _find_row_precisely(row, nested_name, 0)  # Раньше: Так функция сперва изет Next, а потом -- Previous. Т.о., максимальная скорость (если строки не найдется, то фейл теста -- можно и потратить время на previous-поиск)
            found_elem = row
        else:
            found_elem = _find_row_precisely(self, row_name, 1)
        return found_elem


