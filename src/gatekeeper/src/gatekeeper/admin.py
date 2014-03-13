# -*- coding: utf-8 -*-

import datetime
import transaction
from . import SESSION_KEY
from cromlech.security import Interaction
from cromlech.browser import IPublicationRoot
from cromlech.browser import setSession
from cromlech.dawnlight import ViewLookup
from cromlech.dawnlight import traversable, DawnlightPublisher
from cromlech.sqlalchemy import create_and_register_engine
from cromlech.sqlalchemy import SQLAlchemySession
from cromlech.webob import Request
from dolmen.content import schema
from dolmen.sqlcontainer import SQLContainer
from dolmen.view import query_view
from grokcore.security import require
from sqlalchemy import Column, Text, Integer, DateTime, String
from sqlalchemy.ext.declarative import declarative_base
from zope.interface import Interface, implementer
from zope.location import Location
import zope.schema
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm
from cromlech.dawnlight import query_view


view_lookup = ViewLookup(query_view)

Admin = declarative_base()


ALERT = u"alert"
INFO = u"infos"
ADVERT = u"advert"

ON_DATES = u"on_dates"
DISABLED = u"disabled"
ENABLED = u"enabled"


MODES = SimpleVocabulary((
    SimpleTerm(title="Always", value=ENABLED),
    SimpleTerm(title="Time span", value=ON_DATES),
    SimpleTerm(title="Disabled", value=DISABLED),
    ))


TYPES = SimpleVocabulary((
    SimpleTerm(title=u"Alert", value=ALERT),
    SimpleTerm(title=u"Information", value=INFO),
    SimpleTerm(title=u"Advertisement", value=ADVERT),
    ))


def now():
    return datetime.datetime.now()


class IMessage(Interface):

    id = zope.schema.Int(
        title=u"Unique identifier",
        readonly=True,
        required=True)

    message = zope.schema.Text(
        title=u"Message",
        required=True)

    type = zope.schema.Choice(
        title=u"Type of message",
        vocabulary=TYPES,
        default=INFO,
        required=True)

    activation = zope.schema.Choice(
        title=u"Type of message",
        vocabulary=MODES,
        default=ON_DATES,
        required=True)

    enable = zope.schema.Datetime(
        title=u"Date of activation",
        description=u"Set empty for an immediate activation",
        required=False)

    disable = zope.schema.Datetime(
        title=u"Date of de-activation",
        description=u"Set empty for an immediate de-activation",
        required=False)


class Message(Location, Admin):
    schema(IMessage)
    require('zope.Public')

    __tablename__ = 'messages'

    id = Column('id', Integer, primary_key=True)
    message = Column('message', Text, nullable=False)
    type = Column('type', String(32), nullable=False)
    activation = Column('activation', String(32), nullable=False)
    enable = Column('enable', DateTime, nullable=False, default=now())
    disable = Column('disable', DateTime, nullable=False, default=now())


class MessagesRoot(SQLContainer):
    factory = model = Message


@implementer(IPublicationRoot)
class AdminRoot(Location):
    traversable('messages')

    def __init__(self, pkey, dbkey):
        self.pkey = pkey
        self.messages = MessagesRoot(self, 'messages', dbkey)


def get_valid_messages(session):
    limit = now()
    enabled = session.query(Message).filter(Message.activation == ENABLED)
    valid = session.query(Message).filter(
        Message.activation == ON_DATES).filter(
        Message.enable <= limit).filter(Message.disable >= limit)
    return iter(enabled.union(valid))


def admin(global_conf, dburl, dbkey, pkey, **kwargs):

    engine = create_and_register_engine(dburl, dbkey)
    engine.bind(Admin)
    Admin.metadata.create_all()

    root = AdminRoot(pkey, dbkey)
    publisher = DawnlightPublisher(view_lookup=view_lookup)

    def app(environ, start_response):
        session = environ[SESSION_KEY].session
        setSession(session)
        request = Request(environ)
        with Interaction():
            with transaction.manager as tm:
                with SQLAlchemySession(engine, transaction_manager=tm):
                    response = publisher.publish(
                        request, root, handle_errors=True)
                    result = response(environ, start_response)
        setSession()
        return result
    return app
