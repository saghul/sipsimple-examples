
from __future__ import with_statement

import os
import random
import urllib

from application import log
from application.notification import IObserver, NotificationCenter
from application.python.util import Singleton, Null
from itertools import cycle
from sipsimple.threading.green import run_in_green_thread
from sylk.applications import ISylkApplication, sylk_application
from sylk.applications.chucknorrismessenger2.parser import ChuckNorrisParser
from zope.interface import implements

@sylk_application
class ChuckNorrisMessengerApplication2(object):
    __metaclass__ = Singleton
    implements(ISylkApplication, IObserver)

    __appname__ = 'chucknorrismessenger2'

    def __init__(self):
        parser = ChuckNorrisParser()
        for i in [random.randint(1, 100) for i in xrange(5)]:
            try:
                data = urllib.urlopen("http://4q.cc/index.php?pid=listfacts&person=chuck&page=%d" % i).read()
            except IOError:
                break
            else:
                parser.parse(data)
        facts = parser.facts
        if not facts:
            try:
                facts = open(os.path.realpath(os.path.join(os.path.dirname(__file__), 'facts.txt')), 'r').read().split('\n')
            except IOError:
                facts = []
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), 'facts.txt')), 'w') as f:
            f.write('\n'.join(facts))
        log.msg('%d Chuck Norris facts loaded!' % len(facts))
        random.shuffle(facts)
        self.facts = cycle(facts)

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
        try:
            fact = self.facts.next()
        except StopIteration:
            return
        chat_stream = notification.sender
        chat_stream.send_message(fact)

