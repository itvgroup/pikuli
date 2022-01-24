# -*- coding: utf-8 -*-

import time

import numpy as np
import cv2

from pikuli import settings, FindFailed, FailExit, logger
from pikuli._functions import verify_timeout_argument
from .pattern import Pattern
from .file import File
from .match import Match

# Время в [c] между попытками распознования графического объекта
DELAY_BETWEEN_CV_ATTEMPT = 1.0
DEFAULT_FIND_TIMEOUT = 3.1

def _get_list_of_patterns(ps, failExitText):
    if not isinstance(ps, list):
        ps = [ps]
    for i, p in enumerate(ps):
        try:
            ps[i] = Pattern(p)
        except Exception as ex:
            raise FailExit(failExitText + '\n\t' + ' ' * 20 + str(ex))
    return ps

class RegionCVMethods:

    '''
            find_timeout      --  Значение по умолчанию, которове будет использоваться, если метод find() (и подобные) этого класса вызван без явного указания timeout.
                                  Если не передается конструктуру, то берется из переменной модуля DEFAULT_FIND_TIMEOUT.
                                  Будет наслодоваться ко всем объектам, которые возвращаются методами этого класса.
    '''

    def __init__(self, reg_owner):  #: Region):
        self._reg_owner = reg_owner
        self._find_timeout = DEFAULT_FIND_TIMEOUT

    def take_screenshot(self):
        return np.array(self._reg_owner.take_screenshot().pillow_img)

    def __find(self, ps, field):
        # cv2.imshow('field', field)
        # cv2.imshow('pattern', ps._cv2_pattern)
        # cv2.waitKey(3*1000)
        # cv2.destroyAllWindows()

        CF = 0
        try:
            if CF == 0:
                res = cv2.matchTemplate(field, ps._cv2_pattern, cv2.TM_CCORR_NORMED)
                loc = np.where(res > ps.similarity)  # 0.995
            elif CF == 1:
                res = cv2.matchTemplate(field, ps._cv2_pattern, cv2.TM_SQDIFF_NORMED)
                loc = np.where(res < 1.0 - ps.similarity)  # 0.005
        except cv2.error as ex:
            raise FindFailed('OpenCV ERROR: ' + str(ex), patterns=ps, field=field, cause=FindFailed.OPENCV_ERROR)

        # for pt in zip(*loc[::-1]):
        #    cv2.rectangle(field, pt, (pt[0] + self._w, pt[1] + self._h), (0, 0, 255), 2)
        # cv2.imshow('field', field)
        # cv2.imshow('pattern', ps._cv2_pattern)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

        # 'res' -- Матрица, где каждый элемент содержит корреляуию кусочка "поля" с шаблоном. Каждый элемент
        #          матрицы соответствует пикселю из "поля". Индексация, вестимо, от нуля.
        # 'loc' -- структура вида (array([264, 284, 304]), array([537, 537, 537])) где три пары индексов элементов матрицы 'res',
        #          для которых выполняется условие. Если из zip'нуть, то получиться [(264, 537), (284, 537), (304, 537)].
        # Т.о. каждый tuple в zip'е ниже будет иметь три элемента: индекс по 'x', индекс по 'y' и 'score'.

        '''x_arr = map(lambda x: int(x) + self._x, loc[1])
        y_arr = map(lambda y: int(y) + self._y, loc[0])
        s_arr = map(lambda s: float(s), res[loc[0], loc[1]])
        return zip(x_arr, y_arr, s_arr)'''

        return map(lambda x, y, s: (int(x) + self._reg_owner.x, int(y) + self._reg_owner.y, float(s)), loc[1], loc[0], res[loc[0], loc[1]])

    def findAll(self, ps, delay_before=0):
        '''
        Если ничего не найдено, то вернется пустой list, и исключения FindFailed не возникнет.
        '''
        err_msg_template = '[error] Incorect \'findAll()\' method call:\n\tps = %s\n\ttypeOf ps=%s\n\tdelay_before = %s\n\tadditional comment: %%s' % (str(ps),type(ps), str(delay_before))

        try:
            delay_before = float(delay_before)
        except ValueError:
            raise FailExit(err_msg_template % 'delay_before is not float')

        ps = _get_list_of_patterns(ps, err_msg_template % 'bad \'ps\' argument; it should be a string (path to image file) or \'Pattern\' object')

        time.sleep(delay_before)
        (pts, self._last_match) = ([], [])
        try:
            for p in ps:
                pts.extend( self.__find(p, self.take_screenshot()) )
                self._last_match.extend( map(lambda pt: Match(pt[0], pt[1], p._w, p._h, p, pt[2]), pts) )

        except FindFailed as ex:
            dt = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

            fn_field = os.path.join(settings.getFindFailedDir(), 'Region-findAll-field-'   + dt + '-' + '+'.join([Pattern(p).getFilename(full_path=False) for p in ps]) + '.jpg')
            cv2.imwrite(fn_field, ex.field, [cv2.IMWRITE_JPEG_QUALITY, 70])

            fn_pattern = []
            for p in ex.patterns:
                fn_pattern += [os.path.join(settings.getFindFailedDir(), 'Region-findAll-pattern-' + dt + '-' + p.getFilename(full_path=False) + '.jpg')]
                cv2.imwrite(fn_pattern[-1], p._cv2_pattern, [cv2.IMWRITE_JPEG_QUALITY, 70])

            logger.info('pikuli.Region.findAll: FindFailed; ps = {}'
                        '\n\tField stored as:\n\t\t[[f]]'
                        '\n\tPatterns strored as:\n\t\t{}'.format(ps, '\b\t\t'.join(['[[f]]'] * len(fn_pattern))),
                        extra={'f': [File(fn_field)] + [File(f) for f in fn_pattern]})

            raise ex
        else:
            scores = '[' + ', '.join(['%.2f'%m.score for m in self._last_match]) + ']'
            logger.info('pikuli.findAll: total found {} matches of <{}> in {}; scores = {}'.format(
                len(self._last_match), str(ps), str(self), scores))
            return self._last_match

    def _wait_for_appear_or_vanish(self, ps, timeout, aov, exception_on_find_fail=None):
        '''
            ps может быть String или List:
              -- Если ps - это список (list) и aov == 'appear', то возвращается первый найденный элемент. Это можно использвоать, если требуется найти любое из переданных изображений.
              -- Если ps - это список (list) и aov == 'vanish', то функция завершается, когда не будет найден хотя бы один из шаблонов.

            exception_on_find_fail -- необязательный аргумент True|False. Здесь нужен только для кастопизации вывода в лог в случае ненахождения паттерна.
        '''
        ps = _get_list_of_patterns(ps, 'bad \'ps\' argument; it should be a string (path to image file) or \'Pattern\' object: %s' % str(ps))

        if self.w == 0:
            raise FailExit('bad rectangular area: self.w == 0')
        if self.h == 0:
            raise FailExit('bad rectangular area: self.h == 0')

        if timeout is None:
            timeout = self._find_timeout
        else:
            try:
                timeout = float(timeout)
                if timeout < 0:
                    raise ValueError
            except ValueError:
                raise FailExit('bad argument: timeout = \'%s\'' % str(timeout))

        prev_field = None
        elaps_time = 0
        while True:
            field = self.take_screenshot()

            if prev_field is None or (prev_field != field).all():
                for _ps_ in ps:
                    pts = self.__find(_ps_, field)
                    if aov == 'appear':
                        if len(pts) != 0:
                            # Что-то нашли. Выберем один вариант с лучшим 'score'. Из несольких с одинаковыми 'score' будет первый при построчном проходе по экрану.
                            pt = max(pts, key=lambda pt: pt[2])
                            logger.info( 'pikuli.%s.<find...>: %s has been found' % (type(self).__name__, _ps_.getFilename(full_path=False)))
                            return Match(pt[0], pt[1], _ps_._w, _ps_._h, _ps_, pt[2])
                    elif aov == 'vanish':
                        if len(pts) == 0:
                            logger.info( 'pikuli.%s.<find...>: %s has vanished' % (type(self).__name__, _ps_.getFilename(full_path=False)))
                            return
                    else:
                        raise FailExit('unknown \'aov\' = \'%s\'' % str(aov))

            time.sleep(DELAY_BETWEEN_CV_ATTEMPT)
            elaps_time += DELAY_BETWEEN_CV_ATTEMPT
            if elaps_time >= timeout:
                logger.info( 'pikuli.%s.<find...>: %s hasn\'t been found' % (type(self).__name__, _ps_.getFilename(full_path=False)) +
                     ', but exception was disabled.' if exception_on_find_fail is not None and not exception_on_find_fail else '' )
                #TODO: Какие-то ту ошибки. Да и следует передавать, наверно, картинки в FindFailed(), а где-то из модулей робота сохранять, если надо.

                failedImages = ', '.join(map(lambda p: p.getFilename(full_path=True), ps))
                raise FindFailed(
                    "Unable to find '{}' in {} after {} secs of trying".format(failedImages, self, elaps_time),
                    patterns=ps, field=field
                )

    def find(self, ps, timeout=None, exception_on_find_fail=True, save_img_file_at_fail=None):
        '''
        Ждет, пока паттерн не появится.

        timeout определяет время, в течение которого будет повторяься неудавшийся поиск. Возможные значения:
            timeout = 0     --  однократная проверка
            timeout = None  --  использование дефолтного значения
            timeout = <число секунд>

        Возвращает Region, если паттерн появился. Если нет, то:
            a. исключение FindFailed при exception_on_find_fail = True
            b. возвращает None при exception_on_find_fail = False.

        save_img_file_at_fail  --  Сохранять ли картинки при ошибке поиска: True|False|None. None -- значение берется из exception_on_find_fail.
        '''
        try:
            self._last_match = self._wait_for_appear_or_vanish(ps, timeout, 'appear', exception_on_find_fail=exception_on_find_fail)

        except FailExit:
            self._last_match = None
            raise FailExit('\nNew stage of %s\n[error] Incorect \'find()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))

        except FindFailed as ex:
            if save_img_file_at_fail or save_img_file_at_fail is None and exception_on_find_fail:
                if not isinstance(ps, list):
                    ps = [ps]
                dt = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

                fn_field   = os.path.join(settings.getFindFailedDir(), 'Region-find-field-'   + dt + '-' + '+'.join([Pattern(p).getFilename(full_path=False) for p in ps]) + '.jpg')
                cv2.imwrite(fn_field, ex.field, [cv2.IMWRITE_JPEG_QUALITY, 70])

                fn_pattern = []
                for p in ex.patterns:
                    fn_pattern += [os.path.join(settings.getFindFailedDir(), 'Region-find-pattern-' + dt + '-' + p.getFilename(full_path=False) + '.jpg')]
                    cv2.imwrite(fn_pattern[-1], p._cv2_pattern, [cv2.IMWRITE_JPEG_QUALITY, 70])

                logger.info('pikuli.Region.find: FindFailed; ps = {}'
                            '\n\tField stored as:\n\t\t[[f]]'
                            '\n\tPatterns strored as:\n\t\t{}'.format(ps, '\b\t\t'.join(['[[f]]'] * len(fn_pattern))),
                            extra={'f': [File(fn_field)] + [File(f) for f in fn_pattern]})

            else:
                logger.info('pikuli.Region.find: FindFailed; exception_on_find_fail = %s; ps = %s' % (str(exception_on_find_fail), str(ps)))

            if exception_on_find_fail or ex.cause != FindFailed.NOT_FOUND_ERROR:
                raise ex
            else:
                return None

        else:
            return self._last_match

    def waitVanish(self, ps, timeout=None):
        ''' Ждет, пока паттерн не исчезнет. Если паттерна уже не было к началу выполнения процедуры, то завершается успешно.
        timeout может быть положительным числом или None. timeout = 0 означает однократную проверку; None -- использование дефолтного значения.'''
        try:
            self._wait_for_appear_or_vanish(ps, timeout, 'vanish')
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'waitVanish()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
        except FindFailed:
            logger.info(str(ps))
            return False
        else:
            return True
        finally:
            self._last_match = None

    def exists(self, ps):
        self._last_match = None
        try:
            self._last_match = self._wait_for_appear_or_vanish(ps, 0, 'appear')
        except FailExit:
            raise FailExit('\nNew stage of %s\n[error] Incorect \'exists()\' method call:\n\tself = %s\n\tps = %s' % (traceback.format_exc(), str(self), str(ps)))
        except FindFailed:
            logger.info(str(ps))
            return False
        else:
            return True

    def wait(self, ps=None, timeout=None):
        ''' Для совместимости с Sikuli. Ждет появления паттерна или просто ждет.
        timeout может быть положительным числом или None. timeout = 0 означает однократную проверку; None -- использование дефолтного значения.'''
        if ps is None:
            if timeout is not None:
                time.sleep(timeout)
        else:
            try:
                self._last_match = self._wait_for_appear_or_vanish(ps, timeout, 'appear')
            except FailExit:
                self._last_match = None
                raise FailExit('\nNew stage of %s\n[error] Incorect \'wait()\' method call:\n\tself = %s\n\tps = %s\n\ttimeout = %s' % (traceback.format_exc(), str(self), str(ps), str(timeout)))
            else:
                return self._last_match

    def getLastMatch(self):
        ''' Возвращает результаты последнего поиска. '''
        if self._last_match is None or self._last_match == []:
            raise FindFailed('getLastMatch() is empty')
        return self._last_match

    def set_find_timeout(self, timeout):
        if timeout is None:
            self._find_timeout = DEFAULT_FIND_TIMEOUT
        else:
            self._find_timeout = verify_timeout_argument(timeout, err_msg='[error] Incorect Region.set_find_timeout() method call')

    def get_find_timeout(self):
        return self._find_timeout

    def find_all_solid_markers_by_piece(self, ps):
        '''
        Ищет все почти solid-color маркеры. Выделяется группа найденных как один маркер --
        это нужно, т.к. шаблон ненмого меньше маркера в картинке и поэтому поиск находит несолько
        в почти одном и том же месте

        Алгоритм: все найденные перекрывающиеся маркеры одного вида -- это один маркер. Его центр --
        это среднее между центрами всех найденных "фантомов". Если два маркера не перекрываются
        между собой, но оба перекрываются с третьтим -- всех троих группируем в один.

        Если ничего не найдено, то возвращается пустой список.
        '''

        if not isinstance(ps, list):
            ps = [ps]

        matches = []  # Список списков. В него будут помещаться
        for p in ps:
            unsorted_matches = self.findAll(p)  # Несгруппированные вхождения шаблона
            grouped_matches = []
            while len(unsorted_matches) > 0:
                next_match = unsorted_matches.pop(0)

                # Добавим next_match в существующую гурппу ...
                logger.info(grouped_matches)
                for g in grouped_matches:
                    for m in g:
                        if abs(m.x - next_match.x) < next_match.w and \
                           abs(m.y - next_match.y) < next_match.h:
                            g.append(next_match)
                            next_match = None
                            break
                    if next_match is None:
                        break

                # ... или созданим для него новую группу.
                if next_match is not None:
                    grouped_matches.append([next_match])

            matches.extend(grouped_matches)

        # Замени группы совпадений на итоговые классы Match:
        for i in range(len(matches)):
            sum_score = sum( [m.score for m in matches[i]] )
            x = sum( [m.x*m.score for m in matches[i]] ) / sum_score
            y = sum( [m.y*m.score for m in matches[i]] ) / sum_score
            matches[i] = Match(x, y, matches[i][0].w, matches[i][0].h, matches[i][0].pattern, sum_score/len(matches[i]))

        return matches
