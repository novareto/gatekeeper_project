# -*- coding: utf-8 -*-

import xmlrpclib
from grokcore.component import provides, global_utility
from zope.interface import Interface, Attribute, implementer


class IPortal(Interface):

    url = Attribute(u'URL of the portal')
    title = Attribute(u'Title of the portal')
    available = Attribute(u'Availability')

    def check_authentication(user, password):
        pass

    def get_roles(user):
        pass


@implementer(IPortal)
class XMLRPCPortal(object):

    available = True
    
    def __init__(self, url, title, backurl):
        self.title = title
        self.url = url
        self.backurl = backurl
        self.server = xmlrpclib.Server(url)
 
    def check_authentication(self, user, password):
        #user = xmlrpclib.Binary(user)
        #password = xmlrpclib.Binary(password)
        return self.server.checkAuth(user, password) is 1

    def get_roles(self, user):
        user = xmlrpclib.Binary(user)
        return self.server.getRolesFor(user, password)


UVCSITE = XMLRPCPortal("http://192.168.2.109:8080/app", u"Uvcsite", "http://uvcsite.novareto.de:8000")
Plone = XMLRPCPortal("http://admin:admin@192.168.2.109:8099/Plone", u"PLONE", "http://plone.novareto.de:8000")
global_utility(UVCSITE, provides=IPortal, name=u'uvcsite', direct=True)
global_utility(Plone, provides=IPortal, name=u'portal', direct=True)
