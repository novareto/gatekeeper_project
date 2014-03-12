# -*- coding: utf-8 -*-

import xmlrpclib
import socket
from zope.interface import Interface, Attribute, implementer


class IPortal(Interface):

    url = Attribute(u'URL of the portal')
    title = Attribute(u'Title of the portal')
    available = Attribute(u'Availability')

    def check_authentication(user, password):
        pass

    def get_roles(user):
        pass

    def get_dashboard(user):
        pass


class TimeoutTransport(xmlrpclib.Transport):
    """
    Custom XML-RPC transport class for HTTP connections, allowing a timeout in
    the base connection.
    """

    def __init__(self, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, use_datetime=0):
        xmlrpclib.Transport.__init__(self, use_datetime)
        self._timeout = timeout

    def make_connection(self, host):
        conn = xmlrpclib.Transport.make_connection(self, host)
        conn.timeout = self._timeout
        return conn


def timeout(default_value):
    def might_timeout(func):
        def just_call_it(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except socket.timeout:
                return default_value
        return just_call_it
    return might_timeout


@implementer(IPortal)
class XMLRPCPortal(object):

    available = True

    def __init__(self, url, title, backurl):
        self.title = title
        self.url = url
        self.backurl = backurl

        # timed connection
        t = TimeoutTransport(timeout=3)
        self.server = xmlrpclib.Server(url, transport=t)

    @timeout(False)
    def check_authentication(self, user, password):
        return self.server.checkAuth(user, password) is 1

    @timeout(None)
    def get_roles(self, user):
        return self.server.getRolesFor(user)

    @timeout(None)
    def get_dashboard(self, user):
        return self.server.getRemoteDashboard(user) % {'url': self.backurl}
