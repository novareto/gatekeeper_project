# -*- coding: utf-8 -*-

import datetime, time, base64
import auth_pubtkt
import os

from M2Crypto import RSA, EVP
from cStringIO import StringIO
from cromlech.browser import IPublicationRoot, redirect_exception_response
from cromlech.browser.exceptions import HTTPRedirect
from cromlech.webob import Response, Request
from grokcore.component import baseclass
from urllib import quote
from uvclight import FAILURE
from uvclight import Form, Actions, Action, Fields, Marker, ISuccessMarker
from uvclight import implementer, context, get_template, View as BaseView
from webob.exc import HTTPFound
from zope.component import getMultiAdapter
from zope.interface import Interface
from zope.location import Location
from zope.schema import TextLine, Password


timeout_template = get_template('timeout.pt', __file__)
unauthorized_template = get_template('unauthorized.pt', __file__)


class ILoginForm(Interface):
    """A simple login form interface.
    """
    login = TextLine(
        title=u"Username",
        required=True,
        )
    
    password = Password(
        title=u"Password",
        required=True,
        )


class IResponseSuccessMarker(ISuccessMarker):
    pass


@implementer(IResponseSuccessMarker)
class ResponseSuccessMarker(Marker):

    def __init__(self, success, response):
        self.success = success
        self.response = response
        self.url = None
        
    def __nonzero__(self):
        return bool(self.success)


class View(BaseView):
    responseFactory = Response
    baseclass()

    def __init__(self, environ, request, template):
        self.context = environ
        self.request = request
        self.template = template


iv = os.urandom(16)


def bauth(val):
    def encrypt(data, key):
        # Zero padding
        if len(data) % 16 != 0:
            data += '\0' * (16 - len(data) % 16);
            buffer = StringIO()
            cipher = EVP.Cipher('aes_128_cbc', key=key, iv=iv, op=1)
            cipher.set_padding(0)
            buffer.write(cipher.update(str(data)))
            buffer.write(cipher.final())
            data = iv + buffer.getvalue()
        return data
    return encrypt(val, 'mKaqGWwAVNnthL6J')


class LogMe(Action):

    def available(self, form):
        return True

    def cook(self, form, login, password, back='/'):
        privkey = RSA.load_key(form.context.pkey)
        val = base64.encodestring(bauth('%s:%s' % (login, password)))
        validtime = datetime.datetime.now() + datetime.timedelta(hours=1)
        validuntil = int(time.mktime(validtime.timetuple()))
        ticket = auth_pubtkt.create_ticket(
            privkey, login, validuntil, tokens=['su'],
            extra_fields=(('bauth', val),))

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
        back = data.get('back', '/')
        
        if form.authenticate(login, password):
            res = self.cook(form, login, password, back)
            return ResponseSuccessMarker(True, res)

        return FAILURE


@implementer(IPublicationRoot)
class Login(Location):

    def __init__(self, global_conf, pkey, **kwargs):
        self.pkey = pkey

    def __call__(self, environ, start_response):
        request = Request(environ)
        form = getMultiAdapter((self, request), Interface, u'loginform')
        return form()(environ, start_response)


class LoginForm(Form):
    context(Login)
    responseFactory = Response

    fields = Fields(ILoginForm)
    actions = Actions(LogMe(u'Authenticated'))

    def authenticate(self, login, password):
        if login == "admin" and password == "admin":
            return login
        return None

    def updateForm(self):
        if self._updated is False:
            action, result = self.updateActions()
            if IResponseSuccessMarker.providedBy(result):
                return result.response
            self.updateWidgets()
            self._updated = True
        return None

    def __call__(self, *args, **kwargs):
        try:
            self.update(*args, **kwargs)
            response = self.updateForm()
            if response is not None:
                return response
            else:
                result = self.render(*args, **kwargs)
                return self.make_response(result, *args, **kwargs)
        except HTTPRedirect, exc:
            return redirect_exception_response(self.responseFactory, exc)


def timeout(global_conf, **kwargs):
    def app(environ, start_response):
        request = Request(environ)
        response = View(environ, request, timeout_template)()
        return response(environ, start_response)
    return app


def unauthorized(global_conf, **kwargs):
    def app(environ, start_response):
        request = Request(environ)
        response = View(environ, request, unauthorized_template)()
        return response(environ, start_response)
    return app
