
from application import log
from application.python.util import Singleton, Null
from application.notification import IObserver, NotificationCenter
from sipsimple.conference import AudioConference
from sylk.applications import ISylkApplication, sylk_application
from zope.interface import implements

@sylk_application
class AudioConfApplication(object):
    __metaclass__ = Singleton
    implements(ISylkApplication, IObserver)

    __appname__ = 'audioconf'

    def __init__(self):
        self.audio_conference = None

    def incoming_session(self, session):
        # Handle incoming INVITE session
        log.msg('Incoming session from %s' % session.remote_identity.uri)
        if self.audio_conference is None:
            self.audio_conference = AudioConference()
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

    def _NH_SIPSessionDidStart(self, notification):
        log.msg('Session started')
        session = notification.sender
        audio_stream = session.streams[0]
        self.audio_conference.add(audio_stream)

    def _NH_SIPSessionDidFail(self, notification):
        log.msg('Session failed')
        NotificationCenter().remove_observer(self, sender=notification.sender)

    def _NH_SIPSessionDidEnd(self, notification):
        log.msg('Session ended')
        session = notification.sender
        audio_stream = session.streams[0]
        self.audio_conference.remove(audio_stream)
        NotificationCenter().remove_observer(self, sender=notification.sender)

