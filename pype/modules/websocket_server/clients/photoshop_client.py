from pype.modules.websocket_server import WebSocketServer
"""
    Stub handling connection from server to client.
    Used anywhere solution is calling client methods.
"""
import json
from collections import namedtuple

class PhotoshopClientStub():

    def __init__(self):
        self.websocketserver = WebSocketServer.get_instance()
        self.client = self.websocketserver.get_client()

    def read(self, layer):
        layers_data = {}
        res = self.websocketserver.call(self.client.call('Photoshop.read'))
        try:
            layers_data = json.loads(res)
        except json.decoder.JSONDecodeError:
            pass

        return layers_data.get(str(layer.id))

    def get_layers(self):
        """
            Returns JSON document with all(?) layers in active document.

        :return: <list of namedtuples>
                    Format of tuple: { 'id':'123',
                                     'name': 'My Layer 1',
                                     'type': 'GUIDE'|'FG'|'BG'|'OBJ'
                                     'visible': 'true'|'false'
        """
        layers = {}
        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.get_layers'))
        print("get_layers:: {}".format(res))
        try:
            layers_data = json.loads(res)
        except json.decoder.JSONDecodeError:
            raise ValueError("Received broken JSON {}".format(res))
        ret = []
        # convert to namedtuple to use dot donation
        for d in layers_data:
            ret.append(namedtuple('Layer', d.keys())(*d.values()))

        return ret

    def get_layers_in_layers(self, layers):
        """
            Return all layers that belong to layers (might be groups).
        :param layers:
        :return: <list of nametduples>
        """
        all_layers = self.get_layers()
        print("get_layers_in_layers {}".format(layers))
        print("get_layers_in_layers len {}".format(len(layers)))
        print("get_layers_in_layers type {}".format(type(layers)))
        ret = []
        layer_ids = [lay.id for lay in layers]
        layer_group_ids = [ll.groupId for ll in layers if ll.group]
        for layer in all_layers:
            if layer.groupId in layer_group_ids:  # all from group
                ret.append(layer)
            if layer.id in layer_ids:
                ret.append(layer)

        return ret


    def select_layers(self, layers):
        layer_ids = [layer.id for layer in layers]

        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.get_layers',
                                        layers=layer_ids)
                                        )

    def get_active_document_name(self):
        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.get_active_document_name'))

        return res

    def set_visible(self, layer_id, visibility):
        print("set_visible {}, {}".format(layer_id, visibility))
        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.set_visible',
                                         layer_id=layer_id,
                                         visibility=visibility))

    def saveAs(self, image_path, ext, as_copy):
        res = self.websocketserver.call(self.client.call
                                        ('Photoshop.saveAs',
                                         image_path=image_path,
                                         ext=ext,
                                         as_copy=as_copy))

    def close(self):
        self.client.close()

