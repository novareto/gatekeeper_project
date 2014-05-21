# -*- coding: utf-8 -*-

import uvclight
import ConfigParser

from cromlech.browser import exceptions, setSession
from cromlech.configuration.utils import load_zcml
from cromlech.i18n import register_allowed_languages
from cromlech.webob.request import Request

from uvclight import IRootObject
from uvclight.backends.sql import SQLAlchemySession, create_engine

from zope.component import getUtility, getGlobalSiteManager
from zope.location import Location

from . import SESSION_KEY, ticket as tlib
from .portals import IPortal, XMLRPCPortal
from .admin import Admin, get_valid_messages, styles


@uvclight.implementer(IRootObject)
class GateKeeper(Location):

    def __init__(self, engine):
        self.engine = engine

    def get_portals(self, request):
        user = request.environment['REMOTE_USER']
        tokens = request.environment['REMOTE_ACCESS']
        for name in tokens:
            gateway = getUtility(IPortal, name=name)
            yield {
                "title": gateway.title,
                "url": gateway.backurl,
                "dashboard": gateway.get_dashboard(user),
                }

    def get_messages(self):
        with SQLAlchemySession(self.engine) as session:
            messages = [
                {'msg': m.message, 'type': m.type, 'style': styles[m.type]}
                for m in get_valid_messages(session)]
        return messages


def keeper(global_conf, pubkey, dburl,
           zcml_file=None, portals=None,
           langs="en,de,fr", **kwargs):

    engine = create_engine(dburl, "admin")
    engine.bind(Admin)

    """A factory used to bootstrap the TrajectApplication.
    As the TrajectApplication will use SQL, we use this
    'once and for all' kind of factory to configure the
    SQL connection and inject the demo datas.
    """
    if zcml_file is not None:
        load_zcml(zcml_file)

    if portals is not None:
        pconfig = ConfigParser.ConfigParser()
        pconfig.read(portals)
        for name in pconfig.sections():
            portal = dict(pconfig.items(name))
            xmlutil = XMLRPCPortal(
                portal['inner'], portal['title'], portal['outer'])
            getGlobalSiteManager().registerUtility(xmlutil, IPortal, name=name)

    allowed = langs.strip().replace(',', ' ').split()
    register_allowed_languages(allowed)
    site = GateKeeper(engine)

    def publisher(environ, start_response):

        @tlib.signed_cookie(pubkey)
        def publish(request, root):
            view = uvclight.query_view(request, site, name=u'index')
            if view is not None:
                return view
            return uvclight.query_view(request, site, name=u'notfound'), None

        session = environ[SESSION_KEY].session
        setSession(session)
        request = Request(environ)
        view, error = publish(request, site)
        if error is not None:
            view = uvclight.query_view(request, site, name=u'unauthorized')
            view.set_message(error.title)
        response = view()

        return response(environ, start_response)
    return publisher
