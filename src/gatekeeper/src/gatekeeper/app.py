# -*- coding: utf-8 -*-

import uvclight
import xmlrpclib
from cromlech.browser import IPublicationRoot
from cromlech.configuration.utils import load_zcml
from cromlech.i18n import register_allowed_languages
from cromlech.webob.request import Request
from zope.location import Location


class GateXMLRPC(object):

    def __init__(self, server_url):
        self.server = xmlrpclib.Server(server_url)

    def can_login(self, login):
        return True

    def services(self):
        return iter(self.server.getServices())

 
@uvclight.implementer(IPublicationRoot)
class GateKeeper(Location):

    def __init__(self, portals):
        self.portals = portals


class Index(uvclight.View):
    uvclight.context(GateKeeper)

    def render(self):
        return u"Gatekeeper fur " + unicode(self.context.portals)


def keeper(global_conf, zcml_file=None, langs="en,de,fr", portals="", **kwargs):
    """A factory used to bootstrap the TrajectApplication.
    As the TrajectApplication will use SQL, we use this
    'once and for all' kind of factory to configure the
    SQL connection and inject the demo datas.
    """
    if zcml_file:
        load_zcml(zcml_file)

    allowed = langs.strip().replace(',', ' ').split()
    register_allowed_languages(allowed)

    portals = [p.strip() for p in portals.split()]
    site = GateKeeper(portals)

    def publisher(environ, start_response):
        request = Request(environ)
        view = uvclight.query_view(request, site, name=u'index')
        if view is None:
            # do something !!
            raise RuntimeError('No view !')
        response = view()
        return response(environ, start_response)
    return publisher




