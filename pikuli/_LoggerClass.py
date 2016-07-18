# -*- coding: utf-8 -*-

'''
    Класс логгера для Pikuli. Все функции Pikuli будут выводить информацию во вне через этот класс.

    Вывод текста осуществляеться через функция print. Можно переклчюать режимы вывода:
        plain text
        html
    Если Pikuli вызывается из Robot Framework'а, то следует включаить режим "html" -- Robot перезватит
    этот вывод и вставит его в отчет. По дороге от print до log-файла через механизм Robot Listener
    (клиентская часть реализована в нашем модуле rf_listener) все эти сообщения будут пост-обработаны и,
    при необходимости, выведены в консоль уже в формате plain text.
'''

'''
    TODO: есть commonLogger.py из python-shared-modules. Может, совместить/доделать/удалить/etc?..
'''

import os
import sys
import inspect
from bs4 import BeautifulSoup

from pikuli import Settings

'''try:
    from p2c_module import text_to_network_relay, p2c_level
except ImportError:
    p2c_level = 1

    def text_to_network_relay(content, content_type):
        pass'''


class LogLevel(object):
    info    = 0
    warning = 1
    error   = 2
    debug   = 3
    trace   = 4


class LoggerClass(object):

    def __init__(self):
        pass

    def log(self, msg, msg_args=[], log_level=LogLevel.info, func_name=None, func_name_pref=None, reprint_last_line=False):
        '''
        Входные аргументы:
            msg             --  Сообщение. Можно использовать спецификаторы "%s", чтобы вставлять вместо них текст из
                                параметра msg_args. (Note: вместо %s может потребовать использвание %%s, если при формировании
                                самого значения аргумента msg используется подставновка через спецификаторы).
            msg_args        --  Набор подстановок в msg. Каждый эдемент списка -- tuple, где первое поле -- сымсловое значенение
                                подставляемых данных (к примеру, путь к файлу), а второе -- сами данные.
            log_level       --  Уровень логирования. Определены в классе LogLevel в этом файле.
            func_name       --  Имя функции, откуда вызвали Logger.log(). Если None, то определяется автоматически.
            func_name_pref  --  Если не None, то в лог пойдет запись вида "pikuli.<func_name_pref>.<func_name>: <msg>".
                                Если None, то: "pikuli.<func_name>: <msg>".

        Смысловые значения подстановок в текст сообщения из msg_args:
            'pattern'       --  В сообщение подставляется имя файла, сожержащего графический шаблон для поиска через OpenCV.
                                Поле данных -- это полный локальный для машины, запускающий тест, путь.

        Уровни логирования, определенные в классе LogLevel (аналогично commonLogger.py из python-shared-modules):
            0  --  info
            1  --  warning
            2  --  error
            3  --  debug
            4  --  trace

        Пример вызова:
            for i in range(5):
                logger.l('msg %i - %%s' % i, msg_args = [('pattern', 'pattern-img-file-%i.png' % i)])
        '''
        try:
            subs = []
            for t, d in msg_args:
                if t == 'pattern':
                    """
                    В title span'а "PIKULI_pattern_file_name" будет записан алетрнативный, укокроченный текст
                    для вывода в консоль (обрабатывается в rf_listener)
                    В title span'а "PIKULI_pattern_preview" будет записан полный локальный путь. Потом наша
                    JS-функция будет заправшивать по необхдимости эту картинку.
                    """
                    file_name = os.path.split(d)[1]
                    subs.append('<span class="PIKULI_HTML_LOG PIKULI_pattern_file_name" title="%s">%s<span class="PIKULI_pattern_preview" title="%s"></span></span>' % (file_name, file_name, d))
                else:
                    subs.append(d)
                    self.log('Unexperted substitution type for log message: %s' % str((t, d)), log_level=LogLevel.warning)

            if func_name is None:
                # Получаем имя функции, из которой вызвали текущий запуск log(...)
                func_name = inspect.getouterframes(inspect.currentframe())[1][3]
            subs = '*** pikuli.' + (func_name_pref + '.') if (func_name_pref is not None) else '' + func_name + ': ' + msg % subs + '\n'
            if reprint_last_line:
                subs = '\033[F' + '\033[2K' + subs

            print subs

        except Exception as ex:
            print('[ERROR] error in Pikuli logging: %s' % str(ex))


    def postprocess_robot_html_log(self, log_file_path):
        '''
        Пост-обработка Robot-файла с HTML-логом:
            -- добваляет CSS стили для всплывающего превью картинок
        '''
        try:
            with open(log_file_path) as log_file:
                soup = BeautifulSoup(log_file, 'lxml')

            style_tag = soup.new_tag('style', medial="all", type="text/css")
            style_tag.string = """/* Styles for Pikuli customisation. */
    span.PIKULI_HTML_LOG{
        /* Empty class to distinguish Pikuli HTML log record. */
    }

    span.PIKULI_pattern_file_name {
        position: relative;
        display: inline-block;
    }

    img.PIKULI_pattern_preview {
        position: absolute;
        top: 1em;
        left: 0;
        visibility: hidden;
    }

    span.PIKULI_pattern_file_name:hover > img.PIKULI_pattern_preview {
        visibility: visible;
    }
    span.PIKULI_pattern_file_name:hover {
        color: blue;
    }"""
            soup.style.insert_before(style_tag)
            with open(log_file_path, "wb") as file:
                file.write(soup.prettify("utf-8"))
        except Exception as ex:
            self.log('ERROR: ' + str(ex))
            return False
        return True

'''                if Settings.getPatternURLTemplate() is None:
                    d_robot.append(d_console[-1])
                else:
                    url = '' '''


# Logger = LoggerClass()
# Logger.postprocess_robot_html_log("/home/voron/Desktop/1/1.html")
