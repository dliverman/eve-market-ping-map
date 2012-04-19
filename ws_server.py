"""
A WebSocket server that listens to EMDR and sends notifications to any
connected users to light up systems.
"""
import zlib
import simplejson
import gevent
from gevent import pywsgi
from gevent import monkey; gevent.monkey.patch_all()
from gevent_zeromq import zmq
from geventwebsocket.handler import WebSocketHandler

def worker(market_str, ws):
    market_json = zlib.decompress(market_str)
    market_data = simplejson.loads(market_json)

    for rowset in market_data['rowsets']:
        for row in rowset['rows']:
            raw_system_id = row[10]
            if not raw_system_id:
                continue

            system_id = str(int(raw_system_id))
            ws.send(system_id)

def websocket_app(environ, start_response):
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)

    # Connect to the first publicly available relay.
    subscriber.connect('tcp://relay-linode-atl-1.eve-emdr.com:8050')
    # Disable filtering.
    subscriber.setsockopt(zmq.SUBSCRIBE, "")

    ws = environ["wsgi.websocket"]

    while True:
        gevent.spawn(worker, subscriber.recv(), ws)
        gevent.sleep(0.1)

server = pywsgi.WSGIServer(
    ("", 8000),
    websocket_app,
    handler_class=WebSocketHandler
)

server.serve_forever()