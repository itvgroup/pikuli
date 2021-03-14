# -*- coding: utf-8 -*-

from pikuli import logger, wait_while_not
from pikuli.input import Key, KeyModifier, InputEmulator, Clipboard
from pikuli.uia import UIAElement

from . import CONTROL_CHECK_TIMEOUT


TEXT_CLEAN_METHODS = ['uia_api', 'end&backspaces', 'home&deletes', 'single_backspace']


class _Enter_Text_method(UIAElement):

    REQUIRED_METHODS = {'get_value': ['type_text', 'enter_text'], 'set_value_api': ['type_text', 'enter_text']}
    _type_text_click = {'click_method': 'click', 'click_location': ('getCenter', None, None), 'enter_text_clean_method': 'end&backspaces'}

    def paste_text(self, text, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        """ Обязательно кликнет, а затем сделат Ctrl+V. Удаления или выделения старого текста нет! """
        buff = Clipboard.get_text_from_clipboard()
        try:
            Clipboard.set_text_to_clipboard(text)
            self.click()
            self.type_text('v', modifiers=KeyModifier.CTRL)
        except:
            raise
        finally:
            Clipboard.set_text_to_clipboard(buff)

    def clear_text(self, clean_method, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        if clean_method is None:
            clean_method = self._type_text_click.get('enter_text_clean_method', None)
        if clean_method is None:
            raise Exception('_Enter_Text_method.enter_text(...): clean_method = None, but self._type_text_click does not contain \'enter_text_clean_method\' field\n\tself._type_text_click = %s' % str(self._type_text_click))

        if clean_method == 'uia_api':
            if hasattr(self, 'set_value_api'):
                self.set_value_api('')
            else:
                raise Exception('_Enter_Text_method.clear_text(...): clean_method = \'%s\', but control \'%s\' does not support \'set_value_api()\' method.' % str(clean_method, str(type(self))))
        elif clean_method == 'end&backspaces':
            self.type_text(Key.END + Key.BACKSPACE*(len(self.get_value())+1), chck_text=False, click=True, p2c_notif=False)
        elif clean_method == 'home&deletes':
            self.type_text(Key.HOME + Key.DELETE*(len(self.get_value())+1), chck_text=False, click=True, p2c_notif=False)
        elif clean_method == 'single_backspace':
            self.type_text(Key.BACKSPACE, chck_text=False, click=True, p2c_notif=False)
        elif clean_method in TEXT_CLEAN_METHODS:
            raise Exception('_Enter_Text_method.clear_text(...): [ITERNAL] [TODO] clean_method = \'%s\' is valid, but has not been realised yet.' % str(clean_method))
        else:
            raise Exception('_Enter_Text_method.clear_text(...): clean_method = {!r}'.format(clean_method))

    def type_text(self, text, modifiers=None, chck_text=False, click=True, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        '''
        Кликнем мышкой в _type_text_click, если click=True, и наберем новый текст без автоматического нажания ENTER'a.
        Результат набора текста по умолчанию проверяется -- за это ответчает агрумент chck_text:
            - chck_text = None     - ожидаем, что туда, куда ввели текст, будет text
            - chck_text = False    - не проверяем, какой текст ввелся
            - chck_text = <строка> - сверяем оставшийся текст со <строка>

        При необходимости надо переопределять _type_text_click в дочерних класах, т.к. кликать, возможно, нужно будет не в центр.
        Структура _type_text_click:
            - имя метода у объекта, возвращаемого self.region
            - args как список (list) для этой функции или None
            - kwargs как словарь (dict) для этой функции или None
        '''
        text = str(text)

        if click:
            self.click()
        InputEmulator.type_text(text, modifiers=modifiers)

        if not (chck_text == False):
            if chck_text is None:
                chck_text = text
            if not wait_while_not(lambda: self.get_value() == str(chck_text), check_timeout):
                raise Exception('_Enter_Text_method.type_text(...): text is still %s, not %s after %s seconds' % (self.get_value(), repr(chck_text), str(check_timeout)))

        if p2c_notif:
            logger.info('pikuli.%s.type_text(): type \'%s\' in %s' % (type(self).__name__, repr(text), str(self)))


    def enter_text(self, text, method='click', clean_method=None, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        '''
        Перезапишет текст в контроле.
        В качестве значения method могут быть:
            -- click  - Кликнем мышкой по строке и введем новый текст c автоматическим нажания ENTER'a. Используется type_text().
            -- invoke - Через UIA. Используется set_value_api().
        clean_method:
            -- None - использовать из структуры self._type_text_click
            -- Одно из значений TEXT_CLEAN_METHODS = ['uia_api', 'end&backspaces', 'home&deletes', 'single_backspace']

        Возвращает:
            -- True, если состяние контрола изменилось.
            -- False, если не пришлось менять состояние контрола.
            -- None можнооставить на перспективу возникновения исключения и exception_on_find_fail=False
        '''
        text = str(text)
        if method == 'click':
            self.region.enter_text(text)
            # if text != self.get_value():
            #     #self.type_text('a', modifiers=KeyModifier.CTRL, chck_text=False, click=True) -- не на всех контролах корректно работает
            #     self.clear_text(clean_method, check_timeout=check_timeout, p2c_notif=p2c_notif)
            #
            #     #if len(self.get_value()) != 0:  --  а если поле не поддается очищению, а сосдение -- очищается (пример: "гриды")? Лучше првоерку убрать -- важен еонечный результа.
            #     #    raise Exception('_Enter_Text_method.enter_text(...): can not clear the text field. It still contains the following: %s' % self.get_value())
            #     self.type_text(text + Key.ENTER, chck_text=False, click=False, p2c_notif=False)
            #     changed = True
            # else:
            #     changed = False
        elif method == 'invoke':
            self.set_value_api(text, p2c_notif=False)
        else:
            raise Exception('_Enter_Text_method.enter_text(...): unsupported method = \'%s\'' % str(method))

        # if p2c_notif:
        #     if changed:
        #         logger.info('pikuli.%s.enter_text(): enter \'%s\' in %s' % (type(self).__name__, repr(text), str(self)))
        #     else:
        #         logger.info('pikuli.%s.enter_text(): \'%s\' is alredy in %s' % (type(self).__name__, repr(text), str(self)))
        # return changed


class _ValuePattern_methods(UIAElement):

    REQUIRED_PATTERNS = {'ValuePattern': ['get_value', 'set_value_api', 'is_readoly']}

    def get_value(self):
        val = self.get_pattern('ValuePattern').CurrentValue
        return None if val is None else str(val)

    def set_value_api(self, text, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        '''
        Возвращает:
            -- True, если состяние контрола изменилось.
            -- False, если не пришлось менять состояние контрола.
            -- None можно оставить на перспективу возникновения исключения и exception_on_find_fail=False
        '''
        text = str(text)
        if self.get_pattern('ValuePattern').CurrentValue != text:
            self.get_pattern('ValuePattern').SetValue(text)
            if not wait_while_not(lambda: self.get_pattern('ValuePattern').CurrentValue == text, check_timeout):
                raise Exception('_ValuePattern_methods.set_value_api(...): valur is still %s, not %s after %s seconds' % (str(self.get_pattern('ValuePattern').CurrentValue), text, str(check_timeout)))
            changed = True
        else:
            changed = False
        if p2c_notif:
            if changed:
                logger.info('pikuli.%s.set_value_api(): set \'%s\' to %s (via ValuePattern)' % (type(self).__name__, repr(text), str(self)))
            else:
                logger.info('pikuli.%s.set_value_api(): \'%s\' is alredy in %s (via ValuePattern)' % (type(self).__name__, repr(text), str(self)))
        return changed

    def is_read_only(self):
        return bool(self.get_pattern('ValuePattern').CurrentIsReadOnly)


class _LegacyIAccessiblePattern_state_methods(UIAElement):

    def is_unavailable(self):
        return bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['UNAVAILABLE'])

    def is_available(self):
        return (not self.is_unavailable())

    def is_focused(self):
        return bool(self.get_pattern('LegacyIAccessiblePattern').CurrentState & STATE_SYSTEM['FOCUSED'])


class _LegacyIAccessiblePattern_value_methods(UIAElement):

    def get_value(self):
        return self.get_pattern('LegacyIAccessiblePattern').CurrentValue

    def set_value_api(self, text, check_timeout=CONTROL_CHECK_TIMEOUT, p2c_notif=True):
        '''
        Возвращает:
            -- True, если состяние контрола изменилось.
            -- False, если не пришлось менять состояние контрола.
            -- None можнооставить на перспективу возникновения исключения и exception_on_find_fail=False
        '''
        text = str(text)
        if self.get_pattern('LegacyIAccessiblePattern').CurrentValue != text:
            self.get_pattern('LegacyIAccessiblePattern').SetValue(text)
            if not wait_while_not(lambda: self.get_pattern('LegacyIAccessiblePattern').CurrentValue == text, check_timeout):
                raise Exception('_LegacyIAccessiblePattern_value_methods.set_value_api(...): value is still %s, not %s after %s seconds' % (str(self.get_pattern('LegacyIAccessiblePattern').CurrentValue), text, str(check_timeout)))
            changed = True
        else:
            changed = False
        if p2c_notif:
            if changed:
                logger.info('pikuli.%s.set_value_api(): set \'%s\' to %s (via LegacyIAccessiblePattern)' % (type(self).__name__, repr(text), str(self)))
            else:
                logger.info('pikuli.%s.set_value_api(): \'%s\' is alredy in %s (via LegacyIAccessiblePattern)' % (type(self).__name__, repr(text), str(self)))
        return changed
