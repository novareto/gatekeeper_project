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
from dolmen.template import TALTemplate
from cromlech.webob import Response, Request


iv = os.urandom(16)


login_template = TALTemplate('login.pt')
timeout_template = TALTemplate('timeout.pt')
unauthorized_template = TALTemplate('unauthorized.pt')


class View(BaseView):
    responseFactory = Response

    def __init__(self, environ, request, template):
        self.context = environ
        self.request = request
        self.template = template


class LoginForm(BaseView):
    responseFactory = Response

    def __init__(self, context, request, values):
        self.context = context
        self.request = request
        self.values = values

    def namespace(self):
        ns = dict(
            view=self,
            title=_(u'Something'),
            user_field='username',
            pass_field='password',
            button='form-button')
        ns.update(self.values)
        return ns


def base_authentication(login, passwd):
    return login == "admin" and passwd == "admin"


class Login(object):

    def __init__(self, auth=base_authentication):
        self.authenticate = auth

    def logged_in_response(self, login, password, camefrom=None):
        path = os.path.dirname(__file__)
        pkey = os.path.join(path, 'pkey')
        privkey = RSA.load_key(pkey)

        val = base64.encodestring(bauth('%s:%s' % (login, password)))
        validtime = datetime.datetime.now() + datetime.timedelta(hours=1)
        validuntil = int(time.mktime(validtime.timetuple()))
        ticket = auth_pubtkt.create_ticket(
            privkey, login, validuntil, tokens=['su'],
            extra_fields=(('bauth', val),))

        res = HTTPFound(location="http://gatekeeper.novareto.de")
        res.set_cookie('auth_pubtkt', quote(ticket), path='/',
                       domain='novareto.de', secure=False)
        return res

    def __call__(self, environ, start_response):
        user = None
        message = "Please login"
        request = Request(environ)

        if user is not None:
            # User is already logged in
            camefrom = request.GET.get('camefrom', '/')
            return request.get_response(HTTPFound(location=camefrom))

        username = request.POST.get('username', '')
        if 'POST' == request.environ['REQUEST_METHOD']:
            ###
            # User is currently posting the login form
            ###
            camefrom = request.POST.get('camefrom', '/')
            password = request.POST.get('password', '')

            user = self.authenticate(username, password)

            if user is not None:
                return self.logged_in_response(username, password, camefrom)
            else:
                message = self.failed_message
        else:
            ###
            # User is not logged in and is not submitting the form.
            ###
            camefrom = request.GET.get('camefrom', '/')

        # default : we render the form
        values = {"username": username,
                  "camefrom": camefrom,
                  "message": message}
        form = LoginForm(self, request, **values)
        name = request.path.split('/')[-1]
        form.__name__ = form.__component_name__ = name
        form.__parent__ = self
        return form()


def timeout(environ, start_response):
    request = Request(environ)
    response = View(environ, request, timeout_template)()
    return response(environ, start_response)


def unauthorized(environ, start_response):
    request = Request(environ)
    response = View(environ, request, unauthorized_template)()
    return response(environ, start_response)


def application(environ, start_response):
    mapper = URLMap()
    mapper['/'] = logger
    mapper['/unauthorized'] = unauthorized
    mapper['/timeout'] = timeout
    return not_found(environ, start_response)
