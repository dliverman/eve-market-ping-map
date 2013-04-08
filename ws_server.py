"""
A WebSocket server that listens to EMDR and sends notifications to any
connected users to light up systems.
"""
import zlib
import argparse
import ujson
import gevent
import zmq.green as zmq
from gevent import pywsgi
from gevent import monkey; gevent.monkey.patch_all()
from geventwebsocket.handler import WebSocketHandler

##########
# Config #
##########

# The ZeroMQ socket to listen for market data from.
RECEIVER_BINDINGS = ['ipc:///tmp/announcer-sender.sock']
# The port to listen for websockets connections on.
WEBSOCKET_PORT = 9000

##################
# Command parser #
##################

parser = argparse.ArgumentParser(
    description="Runs a websocket server, relaying market data pings to "
                "a JS-based websockets map.",
)

parser.add_argument(
    '--receiver', action='append', dest='receivers',
    help="Overrides the default receiver binding (%s)." % RECEIVER_BINDINGS[0])
parser.add_argument(
    '--wsport', action='store', dest='ws_port',
    help="Overrides the default websocket port (%s)." % WEBSOCKET_PORT)

parsed = parser.parse_args()

if parsed.receivers:
    RECEIVER_BINDINGS = parsed.receivers
if parsed.ws_port:
    WEBSOCKET_PORT = parsed.ws_port

###########
# Globals #
###########

# The receiver is a connection to a relay or announcer. We'll only form one
# of these, to save on socket count.
context = zmq.Context()
receiver = context.socket(zmq.SUB)
for binding in RECEIVER_BINDINGS:
    receiver.connect(binding)
# Disable filtering.
receiver.setsockopt(zmq.SUBSCRIBE, "")

# To save on socket count, we'll re-broadcast anything coming in via receiver
# to an inproc PUB/SUB setup. This will keep us down to one TCP connection
# that can service a large number of websocket connections.
sender = context.socket(zmq.PUB)
sender.bind('ipc:///tmp/emdr-map-rebroadcast.sock')

# Allows the IPC socket time to bind, I guess.
gevent.sleep(1)

#################
# Rebroadcaster #
#################


def rebroadcaster_worker(message):
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


def rebroadcaster_greenlet_loop():
    """
    This loop blocks the greenlet while waiting for something to come down
    the pipe. When found, fires off another greenlet to re-broadcast the message
    to any connected inproc SUB sockets.
    """
    while True:
        gevent.spawn(rebroadcaster_worker, receiver.recv())

# Fire up the rebroadcaster greenlet loop, which continuously monitors the
# incoming SUB socket for messages. When one is found, re-broadcast it over
# the inproc PUB socket, for any connected websocket sessions to pick up,
gevent.spawn(rebroadcaster_greenlet_loop)

####################################
# WebSocket app, and the fun stuff #
####################################


def websocket_worker(environ, start_response):
    """
    For each websocket connection, a websocket worker is spawned. Each worker
    connects to the in-process sender PUB socket, and waits for messages. Each
    message will be a single system ID that needs to be re-broadcasted to
    the websocket connection that is patiently waiting.

    We use an inproc SUB socket instead of separate TCP sockets to cut down
    on socket count. This also allows us to do the processing only once per
    connection.
    """

    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)

    # Connect to our in-process re-broadcaster, which pumps out parsed/prepped
    # system IDs that are ready for sending.
    subscriber.connect('ipc:///tmp/emdr-map-rebroadcast.sock')
    # Disable filtering.
    subscriber.setsockopt(zmq.SUBSCRIBE, "")

    # This is a WebSocket object that we can send stuff over.
    try:
        ws = environ["wsgi.websocket"]
    except KeyError:
        # This is not a websocket connection. Redir to the map.
        start_response('301 Moved Permanently',
            [
                ('Content-Type', 'text/html'),
                ('Location', 'http://map.eve-emdr.com/'),
            ]
        )
        return ["Please see http://map.eve-emdr.com/"]

    while True:
        # This will block until messages arrive.
        system_id = subscriber.recv()
        # Send the message
        ws.send(system_id)
    ws.close()

#################################
# Boring gevent webserver stuff #
#################################

print("=" * 80)
print("# EMDRPM WebSocket Server #".center(80))
print("-" * 80)
print("* Listening for messages from %s" % RECEIVER_BINDINGS)
print("* Listening for websockets connections on port %s" % WEBSOCKET_PORT)
print("=" * 80)

server = pywsgi.WSGIServer(
    ("", WEBSOCKET_PORT),
    websocket_worker,
    handler_class=WebSocketHandler
)

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("Stopped.")