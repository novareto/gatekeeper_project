# -*- coding: utf-8 -*-

import datetime, time, base64
import auth_pubtkt
import uvclight
import xmlrpclib

from M2Crypto import RSA
from urllib import unquote

from cromlech.browser import setSession, IPublicationRoot
from cromlech.configuration.utils import load_zcml
from cromlech.i18n import register_allowed_languages
from cromlech.webob.request import Request
from uvclight import get_template
from zope.component import getUtilitiesFor, getUtility
from zope.location import Location

from . import SESSION_KEY
from .login import read_bauth
from .portals import IPortal

keeper_template = get_template('door.pt', __file__)


@uvclight.implementer(IPublicationRoot)
class GateKeeper(Location):

    def __init__(self, pubkey):
        self.pubkey = pubkey

    @property
    def portals(self):
        return getUtilitiesFor(IPortal)


class Index(uvclight.View):
    uvclight.context(GateKeeper)
    template = keeper_template

    def get_authentication(self):
        ticket = self.request.cookies.get('auth_pubtkt')
        if ticket:
            ticket = unquote(ticket)
            pubkey = RSA.load_pub_key(self.context.pubkey)
            fields = auth_pubtkt.parse_ticket(ticket, pubkey)

            # we get the basic auth elements
            auth = read_bauth(fields['bauth'])
            user, password = auth.split(':', 1)

            # we get the working portals
            portals = fields['tokens']
            return user, password, portals
        else:
            raise ValueError('No ticket')
        

    def update(self):
        self.user, self.password, self.portals = self.get_authentication()
            

    def services(self):
        for name in self.portals:
            gateway = getUtility(IPortal, name=name)
            yield gateway


def keeper(global_conf, pubkey, zcml_file=None, langs="en,de,fr", **kwargs):
    """A factory used to bootstrap the TrajectApplication.
    As the TrajectApplication will use SQL, we use this
    'once and for all' kind of factory to configure the
    SQL connection and inject the demo datas.
    """
    if zcml_file:
        load_zcml(zcml_file)

    allowed = langs.strip().replace(',', ' ').split()
    register_allowed_languages(allowed)
    site = GateKeeper(pubkey)

    def publisher(environ, start_response):
        session = environ[SESSION_KEY].session
        setSession(session)
        request = Request(environ)
        view = uvclight.query_view(request, site, name=u'index')
        if view is None:
            # do something !!
            raise RuntimeError('No view !')
        response = view()
        return response(environ, start_response)
    return publisher




