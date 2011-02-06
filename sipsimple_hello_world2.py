
import os
from cmd import Cmd

from application.notification import NotificationCenter, IObserver
from application.python.util import Null
from threading import Event
from zope.interface import implements

from sipsimple.account import AccountManager
from sipsimple.application import SIPApplication
from sipsimple.configuration.backend.file import FileBackend
from sipsimple.core import ToHeader, SIPURI
from sipsimple.lookup import DNSLookup, DNSLookupError
from sipsimple.session import Session
from sipsimple.streams import AudioStream
from sipsimple.threading.green import run_in_green_thread


class TestApplication(object):
    implements(IObserver)

    def __init__(self):
        self.application = SIPApplication()
        self.quit_event = Event()

        notification_center = NotificationCenter()
        notification_center.add_observer(self, sender=self.application)

    def start(self):
        self.application.start(FileBackend(os.path.realpath('test-config')))

    def stop(self):
        self.application.stop()

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_SIPApplicationDidStart(self, notification):
        print 'SIP application started'

    def _NH_SIPApplicationDidEnd(self, notification):
        self.quit_event.set()


class OutgoingCallHandler(object):
    implements(IObserver)

    def __init__(self):
        self.session = None

    @run_in_green_thread
    def call(self, destination):
        if self.session is not None:
            print 'Another session is in progress'
            return
        callee = ToHeader(SIPURI.parse(destination))
        try:
            routes = DNSLookup().lookup_sip_proxy(callee.uri, ['udp']).wait()
        except DNSLookupError, e:
            print 'DNS lookup failed: %s' % str(e)
        else:
            account = AccountManager().default_account
            self.session = Session(account)
            NotificationCenter().add_observer(self, sender=self.session)
            self.session.connect(callee, routes, [AudioStream(account)])

    def hangup(self):
        if self.session is None:
            print 'There is no session to hangup'
            return
        self.session.end()

    def handle_notification(self, notification):
        handler = getattr(self, '_NH_%s' % notification.name, Null)
        handler(notification)

    def _NH_SIPSessionGotRingIndication(self, notification):
        print 'Ringing!'

    def _NH_SIPSessionDidStart(self, notification):
        print 'Session started!'

    def _NH_SIPSessionDidFail(self, notification):
        print 'Failed to connect'
        self.session = None
        NotificationCenter().remove_observer(self, sender=notification.sender)

    def _NH_SIPSessionDidEnd(self, notification):
        print 'Session ended'
        self.session = None
        NotificationCenter().remove_observer(self, sender=notification.sender)


application = TestApplication()
application.start()
call_handler = OutgoingCallHandler()


class Stop(object):
    pass

class Interface(Cmd):
    prompt = 'cli> '
    def emptyline(self):
        return

    def do_call(self, line):
        call_handler.call(line)

    def do_hangup(self, line):
        call_handler.hangup()

    def do_exit(self, line):
        application.stop()
        application.quit_event.wait()
        return Stop

    def postcmd(self, stop, line):
        if stop is Stop:
            return True

interface = Interface()
interface.cmdloop()

