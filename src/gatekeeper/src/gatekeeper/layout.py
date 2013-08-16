# -*- coding: utf-8 -*-

from dolmen.layout import Layout
from grokcore.component import context
from zope.interface import Interface
from cromlech.webob import response
from js.bootstrap import bootstrap
from uvclight import get_template
from dolmen.message import receive


class GateLayout(Layout):
    context(Interface)

    responseFactory = response.Response
    template = get_template('layout.pt', __file__)

    title = u"Gatekeeper"
     
    def __call__(self, content, **namespace):
        bootstrap.need()
        namespace['gatekeeper_messages'] = list(receive())
        return Layout.__call__(self, content, **namespace)
