from pype.modules.websocket_server import WebSocketServer
"""
    Stub handling connection from server to client.
    Used anywhere solution is calling client methods.
"""
import json
from collections import namedtuple


class AfterEffectsServerStub():
    """
        Stub for calling function on client (Photoshop js) side.
        Expects that client is already connected (started when avalon menu
        is opened).
        'self.websocketserver.call' is used as async wrapper
    """

    def __init__(self):
        self.websocketserver = WebSocketServer.get_instance()
        self.client = self.websocketserver.get_client()

    def open(self, path):
        """
            Open file located at 'path' (local).
        Args:
            path(string): file path locally
        Returns: None
        """
        self.websocketserver.call(self.client.call
                                  ('Photoshop.open', path=path)
                                  )

    def read(self, layer, layers_meta=None):
        """
            Parses layer metadata from Headline field of active document
        Args:
            layer: <namedTuple Layer("id":XX, "name":"YYY")
            layers_meta: full list from Headline (for performance in loops)
        Returns:
        """
        if layers_meta is None:
            layers_meta = self.get_layers_metadata()

        return layers_meta.get(str(layer.id))

    def imprint(self, layer, data, all_layers=None, layers_meta=None):
        """
            Save layer metadata to Headline field of active document
        Args:
            layer (namedtuple):  Layer("id": XXX, "name":'YYY')
            data(string): json representation for single layer
            all_layers (list of namedtuples): for performance, could be
                injected for usage in loop, if not, single call will be
                triggered
            layers_meta(string): json representation from Headline
                           (for performance - provide only if imprint is in
                           loop - value should be same)
        Returns: None
        """
        if not layers_meta:
            layers_meta = self.get_layers_metadata()
        # json.dumps writes integer values in a dictionary to string, so
        # anticipating it here.
        if str(layer.id) in layers_meta and layers_meta[str(layer.id)]:
            if data:
                layers_meta[str(layer.id)].update(data)
            else:
                layers_meta.pop(str(layer.id))
        else:
            layers_meta[str(layer.id)] = data

        # Ensure only valid ids are stored.
        if not all_layers:
            all_layers = self.get_layers()
        layer_ids = [layer.id for layer in all_layers]
        cleaned_data = {}

        for id in layers_meta:
            if int(id) in layer_ids:
                cleaned_data[id] = layers_meta[id]

        payload = json.dumps(cleaned_data, indent=4)

        self.websocketserver.call(self.client.call
                                  ('Photoshop.imprint', payload=payload)
                                  )

    def close(self):
        self.client.close()

    def _to_records(self, res):
        """
            Converts string json representation into list of named tuples for
            dot notation access to work.
        Returns: <list of named tuples>
        res(string): - json representation
        """
        try:
            layers_data = json.loads(res)
        except json.decoder.JSONDecodeError:
            raise ValueError("Received broken JSON {}".format(res))
        ret = []
        # convert to namedtuple to use dot donation
        if isinstance(layers_data, dict):  # TODO refactore
            layers_data = [layers_data]
        for d in layers_data:
            ret.append(namedtuple('Layer', d.keys())(*d.values()))
        return ret
