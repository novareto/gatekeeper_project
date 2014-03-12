# -*- coding: utf-8 -*-

import auth_pubtkt
import uvclight
import ConfigParser

from M2Crypto import RSA
from urllib import unquote

from cromlech.browser import exceptions
from cromlech.browser import setSession, IPublicationRoot
from cromlech.configuration.utils import load_zcml
from cromlech.i18n import register_allowed_languages
from cromlech.sqlalchemy import SQLAlchemySession, create_engine
from cromlech.webob.request import Request
from grokcore.component import global_utility
from zope.component import getUtility
from zope.component import getGlobalSiteManager
from zope.location import Location

from . import SESSION_KEY
from .login import read_bauth
from .portals import IPortal, XMLRPCPortal
from .admin import Admin, get_valid_messages


class MissingTicket(exceptions.HTTPForbidden):
    title = u'Security ticket is missing : access forbidden'


@uvclight.implementer(IPublicationRoot)
class GateKeeper(Location):

    def __init__(self, pubkey, engine):
        self.pubkey = pubkey
        self.engine = engine

    def get_tokens(self, request):
        ticket = request.cookies.get('auth_pubtkt')
        if ticket:
            ticket = unquote(ticket)
            pubkey = RSA.load_pub_key(self.pubkey)
            fields = auth_pubtkt.parse_ticket(ticket, pubkey)

            # we get the basic auth elements
            auth = read_bauth(fields['bauth'])
            user, password = auth.split(':', 1)

            # we get the working portals
            portals = fields['tokens']
            return user, password, portals
        else:
            raise MissingTicket(location=None)

    def get_portals(self, request):
        user, password, tokens = self.get_tokens(request)
        for name in tokens:
            gateway = getUtility(IPortal, name=name)
            yield {
                "title": gateway.title,
                "url": gateway.backurl,
                "dashboard": gateway.get_dashboard(user),
                }

    def get_messages(self):
        with SQLAlchemySession(self.engine) as session:
            messages = [m.message for m in get_valid_messages(session)]
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
    site = GateKeeper(pubkey, engine)

    def publisher(environ, start_response):
        session = environ[SESSION_KEY].session
        setSession(session)
        request = Request(environ)
        try:
            view = uvclight.query_view(request, site, name=u'index')
            if view is None:
                view = uvclight.query_view(request, site, name=u'notfound')
            response = view()
        except exceptions.HTTPException, e:
            view = uvclight.query_view(request, site, name=u'unauthorized')
            view.set_message(e.title)
            response = view()

        return response(environ, start_response)
    return publisher
