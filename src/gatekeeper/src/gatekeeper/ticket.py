import hashlib
import base64
import hmac
import os

from urllib import unquote
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA
from Crypto.Signature import PKCS1_v1_5
from cromlech.browser import exceptions
from . import i18n as _ 


class MissingTicket(exceptions.HTTPForbidden):
    title = _(u'Security ticket is missing : access forbidden')


class TicketParseError(Exception):
    """Base class for all ticket parsing errors"""

    def __init__(self, ticket, msg=''):
        self.ticket = ticket
        self.msg = msg
        
    def __str__(self):
        return _('Ticket parse error: %s (%s)') % (self.msg, self.ticket)


class BadTicket(TicketParseError):

    def __init__(self, ticket, msg=_('Invalid ticket format')):
        super(BadTicket, self).__init__(ticket, msg)


class BadSignature(TicketParseError):

    def __init__(self, ticket, msg=_('Invalid ticket format')):
        super(BadSignature, self).__init__(ticket, msg)


def read_key(path, passphrase=None):
    with open(path, "r") as kd:
        if passphrase is not None:
            key = RSA.importKey(kd, passphrase=passphrase)
        else:
            key = RSA.importKey(kd)
    return key


class AESCipher(object):

    def __init__(self, key):
        self.key = key

    @staticmethod
    def pkcs1_pad(data):
        length = AES.block_size - (len(data) % AES.block_size)
        return data + ('\0' * length)

    @staticmethod
    def pkcs1_unpad(data):
        return data.rstrip('\0')

    @staticmethod
    def pkcs7_pad(data):
        length = AES.block_size - (len(data) % AES.block_size)
        return data + (chr(length) * length)

    @staticmethod
    def pkcs7_unpad(data):
        return data[:-ord(data[-1])]

    def encrypt(self, data):
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        length = AES.block_size - (len(data) % AES.block_size)
        encrypted = iv + cipher.encrypt(self.pkcs1_pad(data))    
        return encrypted

    def decrypt(self, data):
        iv = data[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        decoded = cipher.decrypt(data[AES.block_size:])
        return self.pkcs1_unpad(decoded)


def calculate_digest(privkey, data):
    dgst = SHA.new(data)
    pkcs = PKCS1_v1_5.new(privkey)
    sig = pkcs.sign(dgst)
    return base64.b64encode(sig)


def verify_sig(pubkey, data, sig):
    sig = base64.b64decode(sig)
    dgst = SHA.new(data)
    verifier = PKCS1_v1_5.new(pubkey)
    return verifier.verify(dgst, sig)


def parse_ticket(ticket, pubkey):
    i = ticket.rfind(';')
    sig = ticket[i+1:]
    if sig[:4] != 'sig=':
        raise BadTicket(ticket)

    sig = sig[4:]
    data = ticket[:i]

    if not verify_sig(pubkey, data, sig):
        raise BadSignature(ticket)

    try:
        fields = dict(f.split('=', 1) for f in data.split(';'))
    except ValueError:
        raise BadTicket(ticket)

    if 'uid' not in fields:
        raise BadTicket(ticket, 'uid field required')

    if 'validuntil' not in fields:
        raise BadTicket(ticket, 'validuntil field required')

    try:
        fields['validuntil'] = int(fields['validuntil'])
    except ValueError:
        raise BadTicket(ticket, 'Bad value for validuntil field')

    if 'tokens' in fields:
        tokens = fields['tokens'].split(',')
        if tokens == ['']:
            tokens = []
        fields['tokens'] = tokens
    else:
        fields['tokens'] = []

    if 'graceperiod' in fields:
        try:
            fields['graceperiod'] = int(fields['graceperiod'])
        except ValueError:
            raise BadTicket(ticket, 'Bad value for graceperiod field')
    
    return fields


def create_ticket(privkey, uid, validuntil, ip=None, tokens=(),
                  udata='', graceperiod=None, extra_fields = ()):
    """Returns signed mod_auth_pubtkt ticket.

    Mandatory arguments:

    ``privkey``:
    Private key object. It must be Crypto.PublicKey.RSA

    ``uid``:
    The user ID. String value 32 chars max.

    ``validuntil``:
    A unix timestamp that describe when this ticket will expire. Integer value.

    Optional arguments:

    ``ip``:
    The IP address of the client that the ticket has been issued for.

    ``tokens``:
    List of authorization tokens.

    ``udata``:
    Misc user data.

    ``graceperiod``:
    A unix timestamp after which GET requests will be redirected to refresh URL.

    ``extra_fields``:
    List of (field_name, field_value) pairs which contains addtional, non-standard fields.
    """

    v = 'uid=%s;validuntil=%d' % (uid, validuntil)
    if ip:
        v += ';cip=%s' % ip
    if tokens:
        v += ';tokens=%s' % ','.join(tokens)
    if graceperiod:
        v += ';graceperiod=%d' % graceperiod
    if udata:
        v += ';udata=%s' % udata
    for k,fv in extra_fields:
        v += ';%s=%s' % (k,fv)
    v += ';sig=%s' % calculate_digest(privkey, v)
    return v


aes = AESCipher('mKaqGWwAVNnthL6J')


def bauth(val):
    return aes.encrypt(val)


def read_bauth(val):
    return aes.decrypt(base64.b64decode(val))


class signed_cookie(object):

    def __init__(self, key):
        self.pubkey = read_key(key)
    
    def __call__(self, func):
        def security_token_reader(request, *args):
            myticket = request.cookies.get('auth_pubtkt')
            if myticket is not None:
                myticket = unquote(myticket)
                fields = parse_ticket(myticket, self.pubkey)

                # we get the basic auth elements
                auth = read_bauth(fields['bauth'])
                user, password = auth.split(':', 1)

                # we get the working portals
                portals = fields['tokens']
                request.environment['REMOTE_USER'] = user
                request.environment['REMOTE_ACCESS'] = portals
                return func(request, *args), None
    
            return None, MissingTicket(location=None)
        return security_token_reader
