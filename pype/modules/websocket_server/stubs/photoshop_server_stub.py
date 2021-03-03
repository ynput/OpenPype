from pype.modules.websocket_server import WebSocketServer
"""
    Stub handling connection from server to client.
    Used anywhere solution is calling client methods.
"""
import json
from collections import namedtuple


class PhotoshopServerStub():
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

    def get_layers(self):
        """
            Returns JSON document with all(?) layers in active document.

        Returns: <list of namedtuples>
                    Format of tuple: { 'id':'123',
                                     'name': 'My Layer 1',
                                     'type': 'GUIDE'|'FG'|'BG'|'OBJ'
                                     'visible': 'true'|'false'
        """
        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.get_layers'))

        return self._to_records(res)

    def get_layers_in_layers(self, layers):
        """
            Return all layers that belong to layers (might be groups).
        Args:
            layers <list of namedTuples>:
        Returns: <list of namedTuples>
        """
        all_layers = self.get_layers()
        ret = []
        parent_ids = set([lay.id for lay in layers])

        for layer in all_layers:
            parents = set(layer.parents)
            if len(parent_ids & parents) > 0:
                ret.append(layer)
            if layer.id in parent_ids:
                ret.append(layer)

        return ret

    def create_group(self, name):
        """
            Create new group (eg. LayerSet)
        Returns: <namedTuple Layer("id":XX, "name":"YYY")>
        """
        ret = self.websocketserver.call(self.client.call
                                        ('Photoshop.create_group',
                                         name=name))
        # create group on PS is asynchronous, returns only id
        layer = {"id": ret, "name": name, "group": True}
        return namedtuple('Layer', layer.keys())(*layer.values())

    def group_selected_layers(self, name):
        """
            Group selected layers into new LayerSet (eg. group)
        Returns: (Layer)
        """
        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.group_selected_layers',
                                         name=name)
                                        )
        res = self._to_records(res)

        if res:
            return res.pop()
        raise ValueError("No group record returned")

    def get_selected_layers(self):
        """
            Get a list of actually selected layers
        Returns: <list of Layer('id':XX, 'name':"YYY")>
        """
        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.get_selected_layers'))
        return self._to_records(res)

    def select_layers(self, layers):
        """
            Selects specified layers in Photoshop by its ids
        Args:
            layers: <list of Layer('id':XX, 'name':"YYY")>
        Returns: None
        """
        layer_ids = [layer.id for layer in layers]

        self.websocketserver.call(self.client.call
                                  ('Photoshop.get_layers',
                                   layers=layer_ids)
                                  )

    def get_active_document_full_name(self):
        """
            Returns full name with path of active document via ws call
        Returns(string): full path with name
        """
        res = self.websocketserver.call(
              self.client.call('Photoshop.get_active_document_full_name'))

        return res

    def get_active_document_name(self):
        """
            Returns just a name of active document via ws call
        Returns(string): file name
        """
        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.get_active_document_name'))

        return res

    def is_saved(self):
        """
            Returns true if no changes in active document
        Returns: <boolean>
        """
        return self.websocketserver.call(self.client.call
                                         ('Photoshop.is_saved'))

    def save(self):
        """
            Saves active document
        Returns: None
        """
        self.websocketserver.call(self.client.call
                                  ('Photoshop.save'))

    def saveAs(self, image_path, ext, as_copy):
        """
            Saves active document to psd (copy) or png or jpg
        Args:
            image_path(string): full local path
            ext: <string psd|jpg|png>
            as_copy: <boolean>
        Returns: None
        """
        self.websocketserver.call(self.client.call
                                  ('Photoshop.saveAs',
                                   image_path=image_path,
                                   ext=ext,
                                   as_copy=as_copy))

    def set_visible(self, layer_id, visibility):
        """
            Set layer with 'layer_id' to 'visibility'
        Args:
            layer_id: <int>
            visibility: <true - set visible, false - hide>
        Returns: None
        """
        self.websocketserver.call(self.client.call
                                  ('Photoshop.set_visible',
                                   layer_id=layer_id,
                                   visibility=visibility))

    def get_layers_metadata(self):
        """
            Reads layers metadata from Headline from active document in PS.
            (Headline accessible by File > File Info)

            Returns:
                (string): - json documents
                example:
                    {"8":{"active":true,"subset":"imageBG",
                          "family":"image","id":"pyblish.avalon.instance",
                          "asset":"Town"}}
                    8 is layer(group) id - used for deletion, update etc.
        """
        layers_data = {}
        res = self.websocketserver.call(self.client.call('Photoshop.read'))
        try:
            layers_data = json.loads(res)
        except json.decoder.JSONDecodeError:
            pass
        return layers_data

    def import_smart_object(self, path, layer_name):
        """
            Import the file at `path` as a smart object to active document.

        Args:
            path (str): File path to import.
            layer_name (str): Unique layer name to differentiate how many times
                same smart object was loaded
        """
        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.import_smart_object',
                                         path=path, name=layer_name))

        return self._to_records(res).pop()

    def replace_smart_object(self, layer, path, layer_name):
        """
            Replace the smart object `layer` with file at `path`
            layer_name (str): Unique layer name to differentiate how many times
                same smart object was loaded

        Args:
            layer (namedTuple): Layer("id":XX, "name":"YY"..).
            path (str): File to import.
        """
        self.websocketserver.call(self.client.call
                                  ('Photoshop.replace_smart_object',
                                   layer_id=layer.id,
                                   path=path, name=layer_name))

    def delete_layer(self, layer_id):
        """
            Deletes specific layer by it's id.
        Args:
            layer_id (int): id of layer to delete
        """
        self.websocketserver.call(self.client.call
                                  ('Photoshop.delete_layer',
                                   layer_id=layer_id))

    def remove_instance(self, instance_id):
        cleaned_data = {}

        for key, instance in self.get_layers_metadata().items():
            if key != instance_id:
                cleaned_data[key] = instance

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
