# -*- coding: utf-8 -*-


import os

class File(object):
    def __init__(self, path):
        if path is None:
            self._path = None
        else:
            self._path = os.path.abspath(path)

    def name_for_plain(self):
        return self._path

    def name_for_html(self):
        # Replaces order is critically important.
        if self._path is not None:
            temp_path = (self._path.replace('&', '&amp;')
                                   .replace('<', '&lt;')
                                   .replace('>', '&gt;'))

            return ('<a href="#" class="PIKULI_pattern_file_name">{0}'
                    '<span class="PIKULI_pattern_preview">'
                    '<img class="PIKULI_pattern_preview" src="/pikuli-image?filename={0}">'
                    '</span></a>'.format(temp_path))
        return '[NO FILE NAME]'

    def getFilename(self, full_path=True):
        if self._path is None:
            return '[NO FILE NAME]'
        if full_path:
            return self._path
        else:
            return os.path.basename(self._path)

