import uvclight

from zope.interface import Interface



class Index(uvclight.View):
    uvclight.context(Interface)

    def render(self):
        return u"HALLO WELT FROM uVCLIht"
