# -*- coding: utf-8 -*-

from pikuli import logger
from ..uia_element import UIAElement


class UIAControl(UIAElement):

    CONTROL_TYPE = None
    LEGACYACC_ROLE = None

    def __init__(self, *args, **kwargs):
        super(UIAControl, self).__init__(*args, **kwargs)

        critical_error = False
        methods_to_block = []
        for c in type(self).mro():
            if hasattr(c, 'REQUIRED_PATTERNS'):
                for (pattern, methods) in c.REQUIRED_PATTERNS.items():
                    if self.get_property('Is'+pattern+'Available') is None:
                        logger.warning('[WARNING] pikuli.ui_element: %s should support \'%s\', but it does not. The following methods will be unavalibale: %s' % (str(self), pattern, ' -- ALL --' if methods is None else str(methods)))
                        if methods is None:
                            critical_error = True
                        else:
                            methods_to_block += methods

            if hasattr(c, 'REQUIRED_METHODS'):
                for (req_method, dep_methods) in c.REQUIRED_METHODS.items():
                    if not hasattr(self, req_method):
                        logger.warning('[WARNING] pikuli.ui_element: %s should have %s() method, but it does not. The following dependent methods will be unavalibale: %s' % (str(self), str(req_method), str(dep_methods)))
                        methods_to_block += methods

        if critical_error:
            raise Exception('pikuli.UIAElement: UIAElement Control %s does not support some vital UIA-patterns. See WARNINGs above.' % str(self))

        for m in methods_to_block:
            if not hasattr(self, m):
                logger.warning('[WARNING] pikuli.ui_element: you try to block method \'%s\' by means of unsupported \'%s\' in %s. But this method does not defined in class \'%s\'. Do you have a mistake in definition of \'%s\'?' % (m, pattern, str(self), type(self).__name__, type(self).__name__))
            else:
                setattr(self, m, self._unavaulable_method_dummy)

    def bring_to_front(self):
        # TODO:
        from pikuli.hwnd import HWNDElement
        self._test4readiness()
        return HWNDElement(self).bring_to_front()

    def click(self, method='click', p2c_notif=True):
        '''
            Эмулирует клин мыши на контролле (method='invoke') или действительно подводит курсор и кликает (method='click'). Реальный клик
            будет просто в цетр области, получаемый из метода reg().
            TODO: !!! invoke пока не реализован !!!
        '''
        if method == 'click':
            try:
                if hasattr(self, 'scroll_into_view'):
                    self.scroll_into_view()
            except Exception as e:
                logger.warn(f"Scroll into view error: {e}")

            if hasattr(self, '_type_text_click'):
                click_location = self._type_text_click['click_location']  # к примеру, метод getTopLeft()
                f = getattr(self.region, click_location[0], None)
                if f is None:
                    raise Exception('_Enter_Text_method.type_text(...): [INTERNAL] wrong \'click_location\':\n\t_type_text_click = %s' % str(_type_text_click))
                if click_location[1] is None:
                    loc = f()
                elif click_location[2] is None:
                    loc = f(*click_location[1])
                else:
                    loc = f(*click_location[1], **click_location[2])

                click_method = getattr(loc, self._type_text_click['click_method'], None)
                if click_method is None:
                    raise Exception('_Enter_Text_method.type_text(...): [INTERNAL] wrong \'click_method\':\n\t_type_text_click = %s' % str(_type_text_click))
                click_method(p2c_notif=False)

                if p2c_notif:
                    logger.info('pikuli.{}.click(): click on {} with method "{}" at location {} = {cl[0]}({cl[1]}, {cl[2]})'.format(
                        type(self).__name__, self, self._type_text_click['click_method'], loc, cl=click_location))

            else:
                self.region.click(p2c_notif=False)
                # if p2c_notif:
                #     logger.info('pikuli.%s.click(): click in center of %s' % (type(self).__name__, str(self)))
        else:
            raise Exception('pikuli.%s.click(): unsupported method = \'%s\'' % (type(self).__name__, str(method)))
