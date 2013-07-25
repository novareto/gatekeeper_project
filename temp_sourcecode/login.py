from webob import Response
from webob.exc import HTTPFound
from webob.dec import wsgify
import datetime, time, base64
import auth_pubtkt
import os
from urllib import quote
from M2Crypto import RSA, EVP
from cStringIO import StringIO


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


@wsgify
def application(request):

    if request.GET.get('timeout'):
        return "Timeout"
    if request.GET.get('unauth'):
        return "You're not authorized"

    path = os.path.dirname(__file__)
    pkey = os.path.join(path, 'pkey')
    privkey = RSA.load_key(pkey)

    login = "admin"
    password = "admin"
    val = base64.encodestring(bauth('%s:%s' % (login, password)))
    #val = base64.encodestring('%s:%s' % (login, password))
    validtime = datetime.datetime.now() + datetime.timedelta(hours=1)
    validuntil = int(time.mktime(validtime.timetuple()))
    ticket = auth_pubtkt.create_ticket(
        privkey, login, validuntil, tokens=['su'], extra_fields=(('bauth', val),))

    res = HTTPFound(location="http://gatekeeper.novareto.de")
    res.set_cookie('auth_pubtkt', quote(ticket), path='/',
                   domain='novareto.de', secure=False)
    return res
