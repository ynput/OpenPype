import uuid
import copy
import json
import threading
from socketserver import TCPServer
from websocket_server import WebSocketHandler, WebsocketServer
from pypeapp import Logger

log = Logger().get_logger(__name__)


class PypeWebSocketHandler(WebSocketHandler):
    client = None
    endpoint = None

    def read_http_headers(self):
        """Get information about client from headers.

        This methodwas overriden to be able get endpoint from request.
        """
        headers = {}
        # first line should be HTTP GET
        http_get = self.rfile.readline().decode().strip()
        http_parts = http_get.split(" ")
        assert not len(http_parts) != 3, (
            "Expected 3 parts of first header line."
        )
        _method, _endpoint, _protocol = http_parts

        # Store endpoint
        self.endpoint = _endpoint

        assert _method.upper().startswith("GET")
        # remaining should be headers
        while True:
            header = self.rfile.readline().decode().strip()
            if not header:
                break
            head, value = header.split(":", 1)
            headers[head.lower().strip()] = value.strip()
        return headers

    def cancel(self):
        """To stop handler's loop."""
        self.keep_alive = False
        if self.client is not None:
            self.server._client_left_(self)
            self.client = None


class Client:
    """Representation of client connected to server.

    Client has 2 immutable atributes `id` and `handler` and `data` which is
    dictionary where additional data to client may be stored.

    Client object behaves as dictionary, all accesses are to `data` attribute.
    Except getting `id`. It is possible to get `id` as attribute or as dict
    item.
    """

    def __init__(self, handler):
        self._handler = handler
        self._id = str(uuid.uuid4())
        self._data = {}
        handler.client = self

    def __getitem__(self, key):
        if key == "id":
            return self.id
        return self._data[key]

    def __setitem__(self, key, value):
        if key == "id":
            raise TypeError("'id' is not mutable attribute.")
        self._data[key] = value

    def __repr__(self):
        return "Client <{}> ({})".format(self.id, self.address)

    def __iter__(self):
        for item in self.items():
            yield item

    def get(self, key, default=None):
        self._data.get(key, default)

    def items(self):
        return self._data.items()

    def values(self):
        return self._data.values()

    def keys(self):
        return self._data.keys()

    def to_dict(self):
        """Converts client to pure dictionary."""
        return {
            "id": self._id,
            "handler": self._handler,
            "data": copy.deepcopy(self._data)
        }

    @property
    def handler(self):
        return self._handler

    @property
    def server(self):
        return self._handler.server

    @property
    def address(self):
        """Client's adress, should be localhost and random port."""
        return self._handler.client_address

    @property
    def endpoint(self):
        """Endpoint where client was registered."""
        return self._handler.endpoint

    @property
    def id(self):
        """Uniqu identifier of client."""
        return self._id

    @property
    def data(self):
        return self.data

    def cancel(self):
        """Stop client's session. This is not API method."""
        self._handler.cancel()
        self._handler = None

    def send_message(self, message):
        self.handler.send_message(message)


class Namespace:
    """Namespace is for implementing custom callbacks for specific url path.

    Args:
        endpoint (str): Url path related to namespace. Determine url path
            required for creating specific session. E.g.: "/my_namespace" means
            that client should connect to the namespace callbacks via url path
            "ws://localhost:{port}/my_namespace".
        server (WebsocketServer): Source server where namespace is registered.
    """
    def __init__(self, endpoint, server=None):
        endpoint_parts = [part for part in endpoint.split("/") if part]
        self.endpoint = "/{}".format("/".join(endpoint_parts))
        self.server = server
        self.clients = {}

    def _new_client(self, client):
        self.clients[client.id] = client
        self.new_client(client)

    def _client_left(self, client):
        if client.id in self.clients:
            self.client_left(client)
            self.clients.pop(client.id, None)

    def new_client(self, client):
        """Possible callback when new client is added."""
        pass

    def client_left(self, client):
        """Possible callback when client left the server."""
        pass

    def on_message(self, message, client):
        """Process of message received from a client."""
        pass

    def send_message(self, client, message):
        """Send message to client, but it can be done directly via client."""
        client.send_message(message)

    def send_message_to_all(self, message, except_ids=[]):
        """Send message to all clients."""
        for client in self.clients.values():
            if except_ids and client.id in except_ids:
                continue
            client.send_message(message)


class ExampleNamespace(Namespace):
    # Called for every client connecting (after handshake)
    def new_client(self, client):
        print("New client connected and was given id {}".format(client["id"]))
        msg = json.dumps({
            "id": client["id"],
            "action": "new_connection"
        })
        client.send_message(msg)

    # Called for every client disconnecting
    def client_left(self, client):
        print("Client({}) disconnected".format(client["id"]))

    # Called when a client sends a message
    def on_message(self, message, client):
        print("Client({}) said: {}".format(client["id"], message))


class PypeWebsocketServer(WebsocketServer):
    """This is simple version of websocket server.

    Server stores all clients connected to server by id using `Client` object.

    It is possible to register namespaces but it is not allowed to have
    multiple namespaces for one url path.

    Note: Websocket server does not work the same way as HTTP servers. It is
    expected opossible access with less registered urls and possiblity
    of storing clients context.

    Args:
        port (int): Port where server should listen.
        host (str): Ip adress of server. "127.0.0.1" means server should be
            accessible only on the same computer. To create accessible server
            for other users in network enter "0.0.0.0".
        handler_klass (WebSocketHandler): Give possitibility to enter another
            handler than PypeWebSocketHandler.

    """
    def __init__(self, port, host="127.0.0.1", handler_klass=None):
        if handler_klass is None:
            handler_klass = PypeWebSocketHandler
        TCPServer.__init__(self, (host, port), handler_klass)
        self.port = self.socket.getsockname()[1]

        self.clients = {}
        self.namespaces = {
            # "/example": ExampleNamespace("/", self)
        }

    def _message_received_(self, handler, msg):
        """Give information to namespace about incomming message."""
        namespace = self.namespaces.get(handler.endpoint)
        if namespace:
            namespace.on_message(msg, handler.client)

    def _new_client_(self, handler):
        """Register new client and give information to namespace if any match.

        If there is not namespace matching client's server then error message
        is sent to client and session is closed.
        """
        client = Client(handler)
        self.clients[client.id] = client
        namespace = self.namespaces.get(handler.endpoint)
        if namespace:
            namespace._new_client(client)
            return

        client.send_message(json.dumps({
            "error": "Namespace '{}' is not registered.".format(
                handler.endpoint
            )
        }))
        client.cancel()

    def _client_left_(self, handler):
        """Remove client from clients and acknowledge namespace."""
        client = handler.client
        if client is None:
            return
        namespace = self.namespaces.get(handler.endpoint)
        if namespace:
            namespace._client_left(client)

        self.clients.pop(client.id, None)

    def _unicast_(self, to_client, msg):
        """Send message to specific client."""
        to_client.handler.send_message(msg)

    def _multicast_(self, msg):
        """Send message to each client connected to server."""
        for client in self.clients.values():
            self._unicast_(client, msg)

    def send_message(self, client, msg):
        """Send message to specific client."""
        self._unicast_(client, msg)

    def send_message_to_all(self, msg):
        """Send message to each client."""
        self._multicast_(msg)

    def start(self):
        """Trigger server to start listen on port."""
        self.run_forever()

    def stop(self):
        """Stop server."""
        self.shutdown()
        self.server_close()


class WebSocketThread(threading.Thread):
    """Wrapper for running websocket server in thread."""
    def __init__(self, port):
        self.server = PypeWebsocketServer(port)
        super(self.__class__, self).__init__()

    def run(self):
        self.server.start()

    def stop(self):
        self.server.stop()
