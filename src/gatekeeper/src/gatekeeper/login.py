# -*- coding: utf-8 -*-

import datetime
import time
import base64
import socket
from Crypto.Cipher import AES

from cStringIO import StringIO
from webob.exc import HTTPFound

from cromlech.browser import redirect_exception_response
from cromlech.browser.exceptions import HTTPRedirect
from cromlech.browser import IView
from cromlech.webob import Request
from cromlech.sqlalchemy import create_engine, SQLAlchemySession
from cromlech.i18n.utils import setLanguage

from dolmen.message import send
from dolmen.forms.base.markers import HIDDEN

from urllib import quote
from uvclight import IRootObject, setSession, query_view
from uvclight import FAILURE, Marker, SuccessMarker, ISuccessMarker
from uvclight import Form, Actions, Action, Fields
from uvclight import baseclass, context, get_template

from zope.component import getUtilitiesFor
from zope.interface import Interface, implementer
from zope.location import Location
from zope.schema import TextLine, Password

from .admin import get_valid_messages, Admin, styles
from . import SESSION_KEY, i18n as _, ticket as tlib
from .portals import IPortal

timeout_template = get_template('timeout.pt', __file__)
unauthorized_template = get_template('unauthorized.pt', __file__)


class ILoginForm(Interface):
    """A simple login form interface.
    """
    login = TextLine(
        title=_(u"Username", default=u"Username"),
        required=True,
    )

    password = Password(
        title=_(u"Password", default=u"Password"),
        required=True,
    )

    back = TextLine(
        title=u"back",
        required=False,
    )



class DirectResponse(Exception):
    
    def __init__(self, response):
        self.response = response


@implementer(IRootObject)
class LoginRoot(Location):

    def __init__(self, pkey, dest, dburl, dbkey):
        self.pkey = pkey
        self.dest = dest
        self.dbkey = dbkey
        self.engine = create_engine(dburl, dbkey)
        self.engine.bind(Admin)

    def get_base_messages(self):
        messages = []
        with SQLAlchemySession(self.engine) as session:
            messages = get_valid_messages(session)
        return messages

    def get_messages(self):
        return [{'msg': m.message, 'type': m.type, 'style': styles[m.type]}
                for m in self.get_base_messages()]



class LogMe(Action):

    def available(self, form):
        return True

    def cook(self, form, login, password, authenticated_for, back):
        privkey = tlib.read_key(form.context.pkey)
        val = base64.b64encode(tlib.bauth('%s:%s' % (login, password)))
        #val = val.replace('\n', '', 1)
        validtime = datetime.datetime.now() + datetime.timedelta(hours=1)
        validuntil = int(time.mktime(validtime.timetuple()))
        ticket = tlib.create_ticket(
            privkey, login, validuntil, tokens=list(authenticated_for),
            extra_fields=(('bauth', val),))

        back = form.request.form.get('form.field.back', back)
        res = HTTPFound(location=back)
        res.set_cookie('auth_pubtkt', quote(ticket), path='/',
                       domain='novareto.de', secure=False)
        return res

    def __call__(self, form):
        data, errors = form.extractData()

        if errors:
            form.submissionError = errors
            return FAILURE

        login = data.get('login')
        password = data.get('password')

        authenticated_for = form.authenticate(login, password)
        if authenticated_for:
            send(_(u'Login successful.'))
            res = self.cook(
                form, login, password, authenticated_for, form.context.dest)
            raise DirectResponse(res)
        else:
            sent = send(_(u'Login failed.'))
            assert sent is True
            url = form.request.url
            return SuccessMarker('LoginFailed', False, url=url)


class BaseLoginForm(Form):
    baseclass()
    context(LoginRoot)

    prefix = ""
    fields = Fields(ILoginForm)
    fields['back'].mode = HIDDEN
    fields['back'].prefix = ""
    actions = Actions(LogMe(_(u'Authenticate'), default=_(u"Authenticate")))
    ignoreRequest = False

    def available(self):
        marker = True
        for message in self.context.get_base_messages():
            if message.type == "alert":
                marker = False
        return marker

    def authenticate(self, login, password):
        gates = getUtilitiesFor(IPortal)
        authenticated_for = set()
        for name, gate in gates:
            try:
                if gate.check_authentication(login, password):
                    authenticated_for.add(name)
            except socket.error:
                print "%r could not be resolved" % name
        return authenticated_for

    def __call__(self, *args, **kwargs):
        try:
            self.update(*args, **kwargs)
            self.updateForm()
            result = self.render(*args, **kwargs)
            return self.make_response(result, *args, **kwargs)
        except HTTPRedirect, exc:
            return redirect_exception_response(self.responseFactory, exc)
        except DirectResponse, exc:
            return exc.response


def login(global_conf, pkey, dest, dburl, dbkey, **kwargs):
    root = LoginRoot(pkey, dest, dburl, dbkey)

    def app(environ, start_response):
        setLanguage('de')
        session = environ[SESSION_KEY].session
        setSession(session)
        request = Request(environ)
        form = query_view(request, root, name=u'loginform')
        response = form()(environ, start_response)
        setSession()
        return response
    return app


def timeout(global_conf, **kwargs):
    def app(environ, start_response):
        setLanguage('de')
        request = Request(environ)
        view = query_view(request, environ, name="timeout")
        response = view()
        return response(environ, start_response)
    return app


def unauthorized(global_conf, **kwargs):
    def app(environ, start_response):
        setLanguage('de')
        request = Request(environ)
        view = query_view(request, environ, name="unauthorized")
        response = view()
        return response(environ, start_response)
    return app
