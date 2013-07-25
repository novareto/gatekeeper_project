# -*- coding: utf-8 -*-

import os
from webob import Response
from webob.dec import wsgify
from dolmen.template import TALTemplate

templatedir = os.path.join(os.path.dirname(__file__))


def get_template(name):
    return TALTemplate(os.path.join(templatedir, name))

template = get_template('dashboard.pt')



class Application(object):

    def get_services_for(self, username):
        return {}

    @wsgify
    def __call__(self, request):
        services = self.get_services(request)
        res = Response(body=template.render(component=self, services=services))
        return res


application = Application()
