# -*- coding: utf-8 -*-

from dolmen.layout import Layout
from grokcore.component import context
from zope.interface import Interface
from cromlech.webob import response


class RawLayout(Layout):
    context(Interface)

    responseFactory = response.Response
    title = u"Returns it all"

    def __call__(self, content, **namespace):
        return content
