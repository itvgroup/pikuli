# -*- coding: utf-8 -*-


from pikuli import wait_while_not, wait_while
from pikuli.uia.adapter import Enums, STATE_SYSTEM
from . import CONTROL_CHECK_TIMEOUT
from .uia_control import UIAControl


class CheckBox(UIAControl):

    CONTROL_TYPE = 'CheckBox'
    REQUIRED_PATTERNS = {}



    def _state(self, method):
        """
        Получаем состояние CheckBox (установлена ли галочка).

        :return: `True`, `False`, `None` (если `ToggleState_Indeterminate` через UIA)
        """
        TOOGLE_STATES_TO_BOOL = {
            Enums.ToggleState.On: True,
            Enums.ToggleState.Off: False,
            Enums.ToggleState.Indeterminate: None
        }
        if method in ['click', 'legacy']:
            curr_state = self.get_pattern('LegacyIAccessiblePattern').CurrentState
            state = bool(curr_state & STATE_SYSTEM['CHECKED'])
        elif method == 'uia':
            toog_state = self.get_pattern('TogglePattern').CurrentToggleState
            state = TOOGLE_STATES_TO_BOOL[toog_state]
        else:
            raise Exception('CheckBox.check(...): unsupported method = \'{}\''.format(method))
        return state

    def _uia_toogle(self):
        """
        Вызывает метод Toogle из TogglePattern. Важно помнить, что может быть 2 или 3 состояния,
        которые этим методом циклически переключаются
        (см. https://msdn.microsoft.com/en-us/library/windows/desktop/ee671459(v=vs.85).aspx)
        """
        res = self.get_pattern('TogglePattern').Toggle()
        # TODO: assert res == UIA.UIA_wrapper.S_OK, 'Toggle res = {}'.format(res)  --  нужен код S_OK.

    def _check_state(self, expected_state, method):
        """
        Проверяем состояние CheckBox (установлена ли галочка).

        :param expected_state: Ожидаемое состояние CheckBox (`True` -- галочка установлена)
        :param str method: Метод проверки: `legacy` -- через `LegacyIAccessiblePattern`, а `uia` --
                           через `TogglePattern`.
        """
        state = self._state(method)
        return expected_state is state

    def _change_state_to(self, target_state, method, check_timeout):
        """
        Изменением состояние CheckBox на желаемое.

        :param bool target_state: Желаемое состояние CheckBox (`True` -- галочка установлена)
        :param str method: Метод проверки: `click` -- через клик в центр контрола, а `uia` --
                           через `TogglePattern`.
        """
        # Если уже, где надо, то просто выходим:
        if self._check_state(target_state, method):
            return False

        # Меняем состояние:
        if method == 'click':
            self.region.click()

        else:  # Метод 'uia':
            init_state = self._state('uia')
            self._uia_toogle()

            # Ждем смены состояния на новое:
            if not wait_while(lambda: self._check_state(init_state, 'uia'), check_timeout):
                raise Exception('CheckBox.uncheck(...): error change state to {}: init = {}, current = {} (timeout {})'.format(
                    target_state, init_state, self._state('uia'), check_timeout))

            # Если сменилось на новое, но не желаемое, значит состояний три и надо еще раз Toogle():
            if not self._check_state(target_state, 'uia'):
                self._uia_toogle()

        # Дожидаемся жалаемого состояния:
        if not wait_while_not(lambda: self._check_state(target_state, method), check_timeout):
            raise Exception('CheckBox.uncheck(...): checkbox is still {} after {} seconds'.format(
                self._state(method), check_timeout))

        return True

    def is_checked(self):
        return self._check_state(True, 'uia')

    def is_unchecked(self):
        return self._check_state(False, 'uia')

    def is_indeterminate(self):
        return self._check_state(None, 'uia')

    def check(self, method='click', check_timeout=CONTROL_CHECK_TIMEOUT):
        """
        Потенциально в качестве значения method могут быть click (подвести курсов мыши и кликнуть) или invoke (через UIA).
        Возвращает:
            -- True, если состяние контрола изменилось.
            -- False, если не пришлось менять состояние контрола.
            -- None можнооставить на перспективу возникновения исключения и exception_on_find_fail=False
        """
        return self._change_state_to(True, method, check_timeout)

    def uncheck(self, method='click', check_timeout=CONTROL_CHECK_TIMEOUT):
        """
        см. описание :func:`CheckBox.check`.
        """
        return self._change_state_to(False, method, check_timeout)

    def check_or_uncheck(self, check_bool, method='click', check_timeout=CONTROL_CHECK_TIMEOUT):
        """
        см. описание :func:`CheckBox.check`.
        """
        if check_bool:
            return self.check(method=method, check_timeout=check_timeout)
        else:
            return self.uncheck(method=method, check_timeout=check_timeout)
