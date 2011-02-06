
from __future__ import with_statement

import twitter

from application import log
from application.notification import IObserver, NotificationCenter
from application.python.util import Singleton, Null
from eventlet.green import httplib, urllib, urllib2
from sipsimple.threading.green import run_in_green_thread
from sylk.applications import ISylkApplication, sylk_application
from zope.interface import implements

# Monkey-patch python-twitter imports so that they are 'green'
twitter.httplib = httplib
twitter.urllib = urllib
twitter.urllib2 = urllib2


@sylk_application
class TwitterSearchApplication(object):
    __metaclass__ = Singleton
    implements(ISylkApplication, IObserver)

    __appname__ = 'twittersearch'

    def __init__(self):
        self.twitter_api = twitter.Api()

    def incoming_session(self, session):
        # Handle incoming INVITE session
        log.msg('Incoming session from %s' % session.remote_identity.uri)
        try:
            chat_stream = (stream for stream in session.proposed_streams if stream.type=='chat').next()
        except StopIteration:
            session.reject(488)
            return
        else:
            NotificationCenter().add_observer(self, sender=session)
            session.accept([chat_stream])

    def incoming_subscription(self, subscribe_request, data):
        # Handle incoming SUBSCRIBE
        pass

    def incoming_sip_message(self, message_request, data):
        # Handle incoming MESSAGE
        pass

    # Handle notifications we receive because we are subscribed to them
    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_SIPSessionDidStart(self, notification):
        log.msg('Session started')
        session = notification.sender
        chat_stream = session.streams[0]
        NotificationCenter().add_observer(self, sender=chat_stream)

    def _NH_SIPSessionDidFail(self, notification):
        log.msg('Session failed')
        NotificationCenter().remove_observer(self, sender=notification.sender)

    def _NH_SIPSessionDidEnd(self, notification):
        log.msg('Session ended')
        session = notification.sender
        chat_stream = session.streams[0]
        notification_center = NotificationCenter()
        notification_center.remove_observer(self, sender=chat_stream)
        notification_center.remove_observer(self, sender=session)

    @run_in_green_thread
    def _NH_ChatStreamGotMessage(self, notification):
        chat_stream = notification.sender
        search_term = chat_stream.session.local_identity.uri.user
        tweets = self.twitter_api.GetSearch(term=search_term)
        text = '\n\n'.join(['%s: %s' % (t.user.screen_name, t.text) for t in tweets])
        chat_stream.send_message(text)

