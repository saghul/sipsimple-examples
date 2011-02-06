
import os

from application import log
from application.python.util import Singleton, Null
from application.notification import IObserver, NotificationCenter
from sipsimple.audio import WavePlayer, WavePlayerError
from sipsimple.threading.green import run_in_green_thread
from sylk.applications import ISylkApplication, sylk_application
from zope.interface import implements

@sylk_application
class JamesBondApplication(object):
    __metaclass__ = Singleton
    implements(ISylkApplication, IObserver)

    __appname__ = 'jamesbond'

    def __init__(self):
        pass

    def incoming_session(self, session):
        # Handle incoming INVITE session
        log.msg('Incoming session from %s' % session.remote_identity.uri)
        try:
            audio_stream = (stream for stream in session.proposed_streams if stream.type=='audio').next()
        except StopIteration:
            session.reject(488)
            return
        else:
            notification_center = NotificationCenter()
            notification_center.add_observer(self, sender=session)
            session.accept([audio_stream])

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

    @run_in_green_thread
    def _NH_SIPSessionDidStart(self, notification):
        log.msg('Session started')
        session = notification.sender
        audio_stream = session.streams[0]
        prompt = os.path.realpath(os.path.join(os.path.dirname(__file__), 'jamesbond.wav'))
        player = WavePlayer(audio_stream.mixer, prompt, pause_time=1, initial_play=False)
        audio_stream.bridge.add(player)
        try:
            player.play().wait()
        except WavePlayerError:
            pass
        audio_stream.bridge.remove(player)
        session.end()

    def _NH_SIPSessionDidFail(self, notification):
        log.msg('Session failed')
        NotificationCenter().remove_observer(self, sender=notification.sender)

    def _NH_SIPSessionDidEnd(self, notification):
        log.msg('Session ended')
        NotificationCenter().remove_observer(self, sender=notification.sender)

