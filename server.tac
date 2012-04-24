"""
WebSocket Echo.

Install: pip install twisted txws

Run: twistd -ny server.tac

Open one of the HTML files under static/
"""
import time

from twisted.python import log
from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.application import internet
from twisted.application.service import Application, Service

from txws import WebSocketFactory
from txZMQ import ZmqEndpoint, ZmqFactory, ZmqPubConnection, ZmqSubConnection
import zlib
import ujson

class EMDRMapPingProtocol(Protocol):
    """
    Echo input back, upper-cased. Define your behaviors in here.
    """
    def dataReceived(self, data):
        log.msg("Got %r" % (data,))
        #self.transport.write(data.upper())

    def connectionMade(self):
        global SESSION_LIST

        SESSION_LIST.append(self)

    def connectionLost(self, reason):
        global SESSION_LIST

        SESSION_LIST.remove(self)


class WebSocketServerFactory(Factory):
    """
    This is used by twisted.internet.TCPServer to create TCP Servers for each
    port the server listens on.
    """
    def __init__(self, service):
        """
        :attr WebSocketService service: Reference to the top-level service.
        :attr EchoUpper protocol: The protocol this factor spawns.
        """
        self.service = service
        self.protocol = EMDRMapPingProtocol


class WebSocketService(Service):
    """
    A simple service that listens on port 8076 for WebSockets traffic.
    """
    def __init__(self):
        self.start_time = time.time()

    def start_service(self, application):
        """
        Gets the show on the road. Fires up a factory, binds the port.
        """
        echofactory = WebSocketServerFactory(self)
        factory = WebSocketFactory(echofactory)
        ws_server = internet.TCPServer(9000, factory)
        ws_server.setName('ws-tcp')
        ws_server.setServiceParent(application)

    def shutdown(self):
        """
        Gracefully shuts down the service.
        """
        reactor.callLater(0, reactor.stop)

class MyZmqSubConnection(ZmqSubConnection):
    def messageReceived(self, message):
        """
        Called on incoming message from ZeroMQ.

        @param message: message data
        """
        if len(message) == 2:
            # compatibility receiving of tag as first part
            # of multi-part message
            self.gotMessage(message[1], message[0])
        else:
            self.gotMessage(*reversed(message[0].split('\0', 1)))

    def gotMessage(self, message, tag=None):
        buf = ''
        if tag:
            buf += tag
            buf += '\0'

        buf += message

        print len(buf)
        outbound_msg = zlib.decompress(buf, -1)

        for session in SESSION_LIST:
            session.transport.write(outbound_msg)


SESSION_LIST = []

zf = ZmqFactory()
e = ZmqEndpoint('connect', 'tcp://master.eve-emdr.com:8050')
s = MyZmqSubConnection(zf, e)
s.subscribe("")


def do_rebroadcaster(message):
    """
    This is ran as a greenlet that parses the incoming data, extracts the
    system numbers, and sends the system IDs over the inproc PUB socket.

    NOTE: This is not the most efficient, but will do for now.

    :param str message: A JSON market data string in Unified Uploader
        Interchange format.
    """
    market_json = zlib.decompress(message)
    market_data = ujson.loads(market_json)

    result_type = market_data['resultType']

    if result_type == 'history':
        # Pewp, we can't do anything with history messages.
        return

    # A list that will contain the IDs of systems to ping. Gets serialized
    # and sent once instead of for each ID.
    ids_to_send = []

    for rowset in market_data['rowsets']:
        for row in rowset['rows']:
            # Column 10 is systemID. I know, hard-coded colum index.
            # I've been a naughty boy.
            raw_system_id = row[10]
            if not raw_system_id:
                # Market data can sometimes lack a system ID, in edge cases.
                continue

            # Make absolutely sure this is an int.
            system_id = int(raw_system_id)
            ids_to_send.append(system_id)

    if ids_to_send:
        # Bombs away. Sends over the WebSocket connection.
        sender.send(ujson.dumps(ids_to_send))

# This is required for the 'twistd' command to be happy.
application = Application("ws-streamer")
ws_service = WebSocketService()
ws_service.start_service(application)

