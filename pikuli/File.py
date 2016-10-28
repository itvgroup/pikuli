# -*- coding: utf-8 -*-


import os

class File(object):
    def __init__(self, path):

        self._path = os.path.abspath(path)

    def name_for_plain(self):
        return self._path

    def name_for_html(self):
        # Replaces order is critically important.
        temp_path = (self._path.replace('&', '&amp;')
                               .replace('<', '&lt;')
                               .replace('>', '&gt;'))

        return ('<a href="#" class="PIKULI_pattern_file_name">{0}'
                '<span class="PIKULI_pattern_preview">'
                '<img src="/pikuli-image?filename={0}">'
                '</span></a>'.format(temp_path))

