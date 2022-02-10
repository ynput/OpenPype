"""
    Stub handling connection from server to client.
    Used anywhere solution is calling client methods.
"""
import sys
import json
import attr
from wsrpc_aiohttp import WebSocketAsync

from avalon.tools.webserver.app import WebServerTool


@attr.s
class PSItem(object):
    """
        Object denoting layer or group item in PS. Each item is created in
        PS by any Loader, but contains same fields, which are being used
        in later processing.
    """
    # metadata
    id = attr.ib()  # id created by AE, could be used for querying
    name = attr.ib()  # name of item
    group = attr.ib(default=None)  # item type (footage, folder, comp)
    parents = attr.ib(factory=list)
    visible = attr.ib(default=True)
    type = attr.ib(default=None)
    # all imported elements, single for
    members = attr.ib(factory=list)
    long_name = attr.ib(default=None)
    color_code = attr.ib(default=None)  # color code of layer


class PhotoshopServerStub:
    """
        Stub for calling function on client (Photoshop js) side.
        Expects that client is already connected (started when avalon menu
        is opened).
        'self.websocketserver.call' is used as async wrapper
    """
    PUBLISH_ICON = '\u2117 '
    LOADED_ICON = '\u25bc'

    def __init__(self):
        self.websocketserver = WebServerTool.get_instance()
        self.client = self.get_client()

    @staticmethod
    def get_client():
        """
            Return first connected client to WebSocket
            TODO implement selection by Route
        :return: <WebSocketAsync> client
        """
        clients = WebSocketAsync.get_clients()
        client = None
        if len(clients) > 0:
            key = list(clients.keys())[0]
            client = clients.get(key)

        return client

    def open(self, path):
        """Open file located at 'path' (local).

        Args:
            path(string): file path locally
        Returns: None
        """
        self.websocketserver.call(
            self.client.call('Photoshop.open', path=path)
        )

    def read(self, layer, layers_meta=None):
        """Parses layer metadata from Headline field of active document.

        Args:
            layer: (PSItem)
            layers_meta: full list from Headline (for performance in loops)
        Returns:
        """
        if layers_meta is None:
            layers_meta = self.get_layers_metadata()

        return layers_meta.get(str(layer.id))

    def imprint(self, layer, data, all_layers=None, layers_meta=None):
        """Save layer metadata to Headline field of active document

        Stores metadata in format:
        [{
            "active":true,
            "subset":"imageBG",
            "family":"image",
            "id":"pyblish.avalon.instance",
            "asset":"Town",
            "uuid": "8"
        }] - for created instances
        OR
        [{
            "schema": "openpype:container-2.0",
            "id": "pyblish.avalon.instance",
            "name": "imageMG",
            "namespace": "Jungle_imageMG_001",
            "loader": "ImageLoader",
            "representation": "5fbfc0ee30a946093c6ff18a",
            "members": [
                "40"
            ]
        }] - for loaded instances

        Args:
            layer (PSItem):
            data(string): json representation for single layer
            all_layers (list of PSItem): for performance, could be
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
        cleaned_data = []

        for layer_id in layers_meta:
            if int(layer_id) in layer_ids:
                cleaned_data.append(layers_meta[layer_id])

        payload = json.dumps(cleaned_data, indent=4)

        self.websocketserver.call(
            self.client.call('Photoshop.imprint', payload=payload)
        )

    def get_layers(self):
        """Returns JSON document with all(?) layers in active document.

        Returns: <list of PSItem>
                    Format of tuple: { 'id':'123',
                                     'name': 'My Layer 1',
                                     'type': 'GUIDE'|'FG'|'BG'|'OBJ'
                                     'visible': 'true'|'false'
        """
        res = self.websocketserver.call(
            self.client.call('Photoshop.get_layers')
        )

        return self._to_records(res)

    def get_layer(self, layer_id):
        """
            Returns PSItem for specific 'layer_id' or None if not found
        Args:
            layer_id (string): unique layer id, stored in 'uuid' field

        Returns:
            (PSItem) or None
        """
        layers = self.get_layers()
        for layer in layers:
            if str(layer.id) == str(layer_id):
                return layer

    def get_layers_in_layers(self, layers):
        """Return all layers that belong to layers (might be groups).

        Args:
            layers <list of PSItem>:

        Returns:
            <list of PSItem>
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
        """Create new group (eg. LayerSet)

        Returns:
            <PSItem>
        """
        enhanced_name = self.PUBLISH_ICON + name
        ret = self.websocketserver.call(
            self.client.call('Photoshop.create_group', name=enhanced_name)
        )
        # create group on PS is asynchronous, returns only id
        return PSItem(id=ret, name=name, group=True)

    def group_selected_layers(self, name):
        """Group selected layers into new LayerSet (eg. group)

        Returns:
            (Layer)
        """
        enhanced_name = self.PUBLISH_ICON + name
        res = self.websocketserver.call(
            self.client.call(
                'Photoshop.group_selected_layers', name=enhanced_name
            )
        )
        res = self._to_records(res)
        if res:
            rec = res.pop()
            rec.name = rec.name.replace(self.PUBLISH_ICON, '')
            return rec
        raise ValueError("No group record returned")

    def get_selected_layers(self):
        """Get a list of actually selected layers.

        Returns: <list of Layer('id':XX, 'name':"YYY")>
        """
        res = self.websocketserver.call(
            self.client.call('Photoshop.get_selected_layers')
        )
        return self._to_records(res)

    def select_layers(self, layers):
        """Selects specified layers in Photoshop by its ids.

        Args:
            layers: <list of Layer('id':XX, 'name':"YYY")>
        """
        layers_id = [str(lay.id) for lay in layers]
        self.websocketserver.call(
            self.client.call(
                'Photoshop.select_layers',
                layers=json.dumps(layers_id)
            )
        )

    def get_active_document_full_name(self):
        """Returns full name with path of active document via ws call

        Returns(string):
            full path with name
        """
        res = self.websocketserver.call(
            self.client.call('Photoshop.get_active_document_full_name')
        )

        return res

    def get_active_document_name(self):
        """Returns just a name of active document via ws call

        Returns(string):
            file name
        """
        return self.websocketserver.call(
            self.client.call('Photoshop.get_active_document_name')
        )

    def is_saved(self):
        """Returns true if no changes in active document

        Returns:
            <boolean>
        """
        return self.websocketserver.call(
            self.client.call('Photoshop.is_saved')
        )

    def save(self):
        """Saves active document"""
        self.websocketserver.call(
            self.client.call('Photoshop.save')
        )

    def saveAs(self, image_path, ext, as_copy):
        """Saves active document to psd (copy) or png or jpg

        Args:
            image_path(string): full local path
            ext: <string psd|jpg|png>
            as_copy: <boolean>
        Returns: None
        """
        self.websocketserver.call(
            self.client.call(
                'Photoshop.saveAs',
                image_path=image_path,
                ext=ext,
                as_copy=as_copy
            )
        )

    def set_visible(self, layer_id, visibility):
        """Set layer with 'layer_id' to 'visibility'

        Args:
            layer_id: <int>
            visibility: <true - set visible, false - hide>
        Returns: None
        """
        self.websocketserver.call(
            self.client.call(
                'Photoshop.set_visible',
                layer_id=layer_id,
                visibility=visibility
            )
        )

    def hide_all_others_layers(self, layers):
        """hides all layers that are not part of the list or that are not 
        children of this list

        Args:
            layers (list): list of PSItem
        """
        extract_ids = set([ll.id for ll in self.get_layers_in_layers(layers)])

        for layer in self.get_layers():
            if layer.visible and layer.id not in extract_ids:
                self.set_visible(layer.id, False)

    def get_layers_metadata(self):
        """Reads layers metadata from Headline from active document in PS.
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
        # format of metadata changed from {} to [] because of standardization
        # keep current implementation logic as its working
        if not isinstance(layers_data, dict):
            temp_layers_meta = {}
            for layer_meta in layers_data:
                layer_id = layer_meta.get("uuid")
                if not layer_id:
                    layer_id = layer_meta.get("members")[0]

                temp_layers_meta[layer_id] = layer_meta
            layers_data = temp_layers_meta
        else:
            # legacy version of metadata
            for layer_id, layer_meta in layers_data.items():
                if layer_meta.get("schema") != "openpype:container-2.0":
                    layer_meta["uuid"] = str(layer_id)
                else:
                    layer_meta["members"] = [str(layer_id)]

        return layers_data

    def import_smart_object(self, path, layer_name, as_reference=False):
        """Import the file at `path` as a smart object to active document.

        Args:
            path (str): File path to import.
            layer_name (str): Unique layer name to differentiate how many times
                same smart object was loaded
            as_reference (bool): pull in content or reference
        """
        enhanced_name = self.LOADED_ICON + layer_name
        res = self.websocketserver.call(
            self.client.call(
                'Photoshop.import_smart_object',
                path=path,
                name=enhanced_name,
                as_reference=as_reference
            )
        )
        rec = self._to_records(res).pop()
        if rec:
            rec.name = rec.name.replace(self.LOADED_ICON, '')
        return rec

    def replace_smart_object(self, layer, path, layer_name):
        """Replace the smart object `layer` with file at `path`

        Args:
            layer (PSItem):
            path (str): File to import.
            layer_name (str): Unique layer name to differentiate how many times
                same smart object was loaded
        """
        enhanced_name = self.LOADED_ICON + layer_name
        self.websocketserver.call(
            self.client.call(
                'Photoshop.replace_smart_object',
                layer_id=layer.id,
                path=path,
                name=enhanced_name
            )
        )

    def delete_layer(self, layer_id):
        """Deletes specific layer by it's id.

        Args:
            layer_id (int): id of layer to delete
        """
        self.websocketserver.call(
            self.client.call('Photoshop.delete_layer', layer_id=layer_id)
        )

    def rename_layer(self, layer_id, name):
        """Renames specific layer by it's id.

        Args:
            layer_id (int): id of layer to delete
            name (str): new name
        """
        self.websocketserver.call(
            self.client.call(
                'Photoshop.rename_layer',
                layer_id=layer_id,
                name=name
            )
        )

    def remove_instance(self, instance_id):
        cleaned_data = {}

        for key, instance in self.get_layers_metadata().items():
            if key != instance_id:
                cleaned_data[key] = instance

        payload = json.dumps(cleaned_data, indent=4)

        self.websocketserver.call(
            self.client.call('Photoshop.imprint', payload=payload)
        )

    def get_extension_version(self):
        """Returns version number of installed extension."""
        return self.websocketserver.call(
            self.client.call('Photoshop.get_extension_version')
        )

    def close(self):
        """Shutting down PS and process too.

            For webpublishing only.
        """
        # TODO change client.call to method with checks for client
        self.websocketserver.call(self.client.call('Photoshop.close'))

    def _to_records(self, res):
        """Converts string json representation into list of PSItem for
        dot notation access to work.

        Args:
            res (string): valid json

        Returns:
            <list of PSItem>
        """
        try:
            layers_data = json.loads(res)
        except json.decoder.JSONDecodeError:
            raise ValueError("Received broken JSON {}".format(res))
        ret = []

        # convert to AEItem to use dot donation
        if isinstance(layers_data, dict):
            layers_data = [layers_data]
        for d in layers_data:
            # currently implemented and expected fields
            ret.append(PSItem(
                d.get('id'),
                d.get('name'),
                d.get('group'),
                d.get('parents'),
                d.get('visible'),
                d.get('type'),
                d.get('members'),
                d.get('long_name'),
                d.get("color_code")
            ))
        return ret
