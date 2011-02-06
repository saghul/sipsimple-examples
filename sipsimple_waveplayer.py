
import os
import sys

from application.notification import NotificationCenter
from optparse import OptionParser
from threading import Event

from sipsimple.account import AccountManager
from sipsimple.application import SIPApplication
from sipsimple.audio import WavePlayer
from sipsimple.configuration.backend.file import FileBackend
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.core import SIPURI, SIPCoreError, ToHeader
from sipsimple.lookup import DNSLookup, DNSLookupError
from sipsimple.session import Session
from sipsimple.streams import AudioStream
from sipsimple.threading.green import run_in_green_thread


class SimpleCallApplication(SIPApplication):
    def __init__(self):
        SIPApplication.__init__(self)
        self.ended = Event()
        self.callee = None
        self.player = None
        self._wave_file = None
        self.session = None
        notification_center = NotificationCenter()
        notification_center.add_observer(self)

    def call(self, options):
        self.callee = options.target
        self._wave_file = options.filename
        self.start(FileBackend('test-config'))

    @run_in_green_thread
    def _NH_SIPApplicationDidStart(self, notification):
        settings = SIPSimpleSettings()
        # We don't need speakers or microphone
        settings.audio.input_device = None
        settings.audio.output_device = None
        settings.save()
        self.player = WavePlayer(SIPApplication.voice_audio_mixer, self._wave_file, loop_count=0, initial_play=False)
        try:
            self.callee = ToHeader(SIPURI.parse(self.callee))
        except SIPCoreError:
            print 'Specified SIP URI is not valid'
            self.stop()
            return
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
        session = notification.sender
        audio_stream = session.streams[0]
        audio_stream.bridge.add(self.player)
        self.player.play()

    def _NH_SIPSessionDidFail(self, notification):
        print 'Failed to connect'
        self.stop()

    def _NH_SIPSessionWillEnd(self, notification):
        session = notification.sender
        audio_stream = session.streams[0]
        self.player.stop()
        audio_stream.bridge.remove(self.player)

    def _NH_SIPSessionDidEnd(self, notification):
        print 'Session ended'
        self.stop()

    def _NH_SIPApplicationDidEnd(self, notification):
        self.ended.set()

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-t', '--target', help='Target URI')
    parser.add_option('-f', '--file', dest='filename', help='File to play', metavar='FILE')
    options, args = parser.parse_args()

    if not options.filename or not options.target:
        print 'Target and filename need to be specified, try --help'
        sys.exit(1)
    if not os.path.isfile(options.filename):
        print "The specified file doesn't exist"
        sys.exit(1)

    application = SimpleCallApplication()
    application.call(options)
    print "Placing call, press Enter to quit the program"
    raw_input()
    if application.session:
        application.session.end()
    application.ended.wait()


