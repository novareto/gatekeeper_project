# -*- coding: utf-8 -*-

from webob.exc import HTTPFound
from webob.dec import wsgify
import datetime, time, base64
import auth_pubtkt
import os
from urllib import quote
from M2Crypto import RSA, EVP
from cStringIO import StringIO
from paste.urlmap import URLMap
from dolmen.view import View as BaseView
from cromlech.webob import Response, Request
from uvclight import get_template


iv = os.urandom(16)


login_template = get_template('login.pt', __file__)
timeout_template = get_template('timeout.pt', __file__)
unauthorized_template = get_template('unauthorized.pt', __file__)


class View(BaseView):
    responseFactory = Response

    def __init__(self, environ, request, template):
        self.context = environ
        self.request = request
        self.template = template


class LoginForm(BaseView):
    responseFactory = Response
    template = login_template

    def __init__(self, context, request, **values):
        self.context = context
        self.request = request
        self.values = values

    def namespace(self):
        ns = dict(
            view=self,
            title=u'Something',
            user_field='username',
            pass_field='password',
            button='form-button')
        ns.update(self.values)
        return ns


def base_authentication(login, passwd):
    if login == "admin" and passwd == "admin":
        return login
    return None


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


class Login(object):

    def __init__(self, global_conf, pkey, **kwargs):
        self.authenticate = base_authentication
        self.pkey = pkey

    def logged_in_response(self, login, password, back):
        privkey = RSA.load_pub_key(self.pkey)

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

    def __call__(self, environ, start_response):
        user = None
        message = "Please login"
        request = Request(environ)

        if user is not None:
            # User is already logged in
            back = request.GET.get('back', '/')
            return request.get_response(HTTPFound(location=back))

        username = request.POST.get('username', '')
        if 'POST' == request.environ['REQUEST_METHOD']:
            ###
            # User is currently posting the login form
            ###
            back = request.POST.get('back', '/')
            password = request.POST.get('password', '')

            user = self.authenticate(username, password)

            if user is not None:
                return self.logged_in_response(username, password, back)(
                    environ, start_response)
            else:
                message = self.failed_message
        else:
            ###
            # User is not logged in and is not submitting the form.
            ###
            back = request.GET.get('back', '/')

        # default : we render the form
        values = {"username": username,
                  "back": back,
                  "message": message}
        form = LoginForm(self, request, **values)
        name = request.path.split('/')[-1]
        form.__name__ = form.__component_name__ = name
        form.__parent__ = self
        return form()(environ, start_response)


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
