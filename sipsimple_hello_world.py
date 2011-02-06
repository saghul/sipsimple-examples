
from application.notification import NotificationCenter
from threading import Event

from sipsimple.account import AccountManager
from sipsimple.application import SIPApplication
from sipsimple.configuration.backend.file import FileBackend
from sipsimple.core import SIPURI, ToHeader
from sipsimple.lookup import DNSLookup, DNSLookupError
from sipsimple.session import Session
from sipsimple.streams import AudioStream
from sipsimple.threading.green import run_in_green_thread


class SimpleCallApplication(SIPApplication):
    def __init__(self):
        SIPApplication.__init__(self)
        self.ended = Event()
        self.callee = None
        self.session = None
        notification_center = NotificationCenter()
        notification_center.add_observer(self)

    def call(self, callee):
        self.callee = callee
        self.start(FileBackend('test-config'))

    @run_in_green_thread
    def _NH_SIPApplicationDidStart(self, notification):
        self.callee = ToHeader(SIPURI.parse(self.callee))
        try:
            routes = DNSLookup().lookup_sip_proxy(self.callee.uri, ['udp']).wait()
        except DNSLookupError, e:
            print 'DNS lookup failed: %s' % str(e)
        else:
            account = AccountManager().default_account
            self.session = Session(account)
            self.session.connect(self.callee, routes, [AudioStream(account)])

    def _NH_SIPSessionGotRingIndication(self, notification):
        print 'Ringing!'

    def _NH_SIPSessionDidStart(self, notification):
        print 'Session started!'

    def _NH_SIPSessionDidFail(self, notification):
        print 'Failed to connect'
        self.stop()

    def _NH_SIPSessionDidEnd(self, notification):
        print 'Session ended'
        self.stop()

    def _NH_SIPApplicationDidEnd(self, notification):
        self.ended.set()

# place an audio call to the specified URI
application = SimpleCallApplication()
application.call("sip:3333@sip2sip.info")
print "Placing call, press Enter to quit the program"
raw_input()
if application.session:
    application.session.end()
application.ended.wait()

