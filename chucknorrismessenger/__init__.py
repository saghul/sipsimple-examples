
from __future__ import with_statement

import os
import random
import urllib

from application import log
from application.python.util import Singleton, Null
from itertools import cycle
from sipsimple.configuration.settings import SIPSimpleSettings
from sipsimple.core import FromHeader, ToHeader, RouteHeader, SIPURI, Message
from sipsimple.lookup import DNSLookup, DNSLookupError
from sipsimple.threading.green import run_in_green_thread
from sylk.applications import ISylkApplication, sylk_application
from sylk.applications.chucknorrismessenger.parser import ChuckNorrisParser
from zope.interface import implements

@sylk_application
class ChuckNorrisMessengerApplication(object):
    __metaclass__ = Singleton
    implements(ISylkApplication)

    __appname__ = 'chucknorrismessenger'

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
        pass

    def incoming_subscription(self, subscribe_request, data):
        # Handle incoming SUBSCRIBE
        pass

    def incoming_sip_message(self, message_request, data):
        # Handle incoming MESSAGE
        from_header = data.headers.get('From', Null)
        to_header = data.headers.get('To', Null)
        content_type = data.headers.get('Content-Type', Null)[0]
        if from_header is Null or to_header is Null:
            message_request.answer(400)
            return
        message_request.answer(200)
        if content_type not in ('text/plain', 'text/html'):
            return
        source_uri = SIPURI.new(to_header.uri)
        destination_uri = SIPURI.new(from_header.uri)
        try:
            fact = self.facts.next()
        except StopIteration:
            return
        else:
            self.send_chuck_norris_fact(source_uri, destination_uri, fact)

    @run_in_green_thread
    def send_chuck_norris_fact(self, source_uri, destination_uri, fact):
        lookup = DNSLookup()
        settings = SIPSimpleSettings()
        try:
            routes = lookup.lookup_sip_proxy(destination_uri, settings.sip.transport_list).wait()
        except DNSLookupError:
            print "DNS lookup error while looking for %s proxy\n" % destination_uri
        else:
            route = routes.pop(0)
            message_request = Message(FromHeader(source_uri),
                                      ToHeader(destination_uri),
                                      RouteHeader(route.get_uri()),
                                      'text/plain',
                                      fact)
            message_request.send()


