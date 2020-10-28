from pype.modules.websocket_server import WebSocketServer
"""
    Stub handling connection from server to client.
    Used anywhere solution is calling client methods.
"""
import json
from collections import namedtuple


import logging
log = logging.getLogger(__name__)

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
                                  ('AfterEffects.open', path=path)
                                  )

    def read(self, layer, layers_meta=None):
        """
            Parses layer metadata from Label field of active document
        Args:
            layer: <namedTuple Layer("id":XX, "name":"YYY")
            layers_meta: full list from Headline (for performance in loops)
        Returns:
        """
        if layers_meta is None:
            layers_meta = self.get_metadata()

        return layers_meta.get(str(layer.id))

    def get_metadata(self):
        layers_data = {}
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_metadata')
                                        )
        try:
            layers_data = json.loads(res)
        except json.decoder.JSONDecodeError:
            raise ValueError("Unparsable metadata {}".format(res))
        return layers_data or {}

    def imprint(self, layer, data, all_layers=None, layers_meta=None):
        """
            Save layer metadata to Label field of metadata of active document
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
            layers_meta = self.get_metadata()

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
            all_layers = self.get_items(False)
        item_ids = [int(item.id) for item in all_layers]
        cleaned_data = {}
        for id in layers_meta:
            if int(id) in item_ids:
                cleaned_data[id] = layers_meta[id]

        payload = json.dumps(cleaned_data, indent=4)

        self.websocketserver.call(self.client.call
                                  ('AfterEffects.imprint', payload=payload)
                                  )

    def get_active_document_full_name(self):
        """
            Returns just a name of active document via ws call
        Returns(string): file name
        """
        res = self.websocketserver.call(self.client.call
                  ('AfterEffects.get_active_document_full_name'))

        return res

    def get_active_document_name(self):
        """
            Returns just a name of active document via ws call
        Returns(string): file name
        """
        res = self.websocketserver.call(self.client.call
                  ('AfterEffects.get_active_document_name'))

        return res

    def get_items(self, layers=True):
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_items',
                                         layers=layers)
                                        )
        return self._to_records(res)

    def import_file(self, path, item_name):
        res = self.websocketserver.call(self.client.call(
                'AfterEffects.import_file',
                path=path,
                item_name=item_name)
              )
        return self._to_records(res).pop()

    def replace_item(self, item, path, item_name):
        """ item is currently comp, might be layer, investigate TODO """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.replace_item',
                                   item_id=item.id,
                                   path=path, item_name=item_name))

    def delete_item(self, item):
        """ item is currently comp, might be layer, investigate TODO """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.delete_item',
                                   item_id=item.id
                                   ))

    def is_saved(self):
        # TODO
        return True

    def save(self):
        """
            Saves active document
        Returns: None
        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.save'))

    def saveAs(self, project_path, as_copy):
        """
            Saves active project to aep (copy) or png or jpg
        Args:
            project_path(string): full local path
            as_copy: <boolean>
        Returns: None
        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.saveAs',
                                   image_path=project_path,
                                   as_copy=as_copy))

    def close(self):
        self.client.close()

    def _to_records(self, res):
        """
            Converts string json representation into list of named tuples for
            dot notation access to work.
        Returns: <list of named tuples>
        res(string): - json representation
        """
        if not res:
            return []

        try:
            layers_data = json.loads(res)
        except json.decoder.JSONDecodeError:
            raise ValueError("Received broken JSON {}".format(res))
        if not layers_data:
            return []

        ret = []
        # convert to namedtuple to use dot donation
        if isinstance(layers_data, dict):  # TODO refactore
            layers_data = [layers_data]
        for d in layers_data:
            ret.append(namedtuple('Layer', d.keys())(*d.values()))
        return ret
