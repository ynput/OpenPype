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
        """
            Get stored JSON with metadata from AE.Metadata.Label field
        Returns:
            (dict)
        """
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
            # loaders create FootageItem now
            all_layers = self.get_items(comps=True,
                                        folders=False,
                                        footages=True)
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
        res = self.websocketserver.call(self.client.call(
              'AfterEffects.get_active_document_full_name'))

        return res

    def get_active_document_name(self):
        """
            Returns just a name of active document via ws call
        Returns(string): file name
        """
        res = self.websocketserver.call(self.client.call(
              'AfterEffects.get_active_document_name'))

        return res

    def get_items(self, comps, folders=False, footages=False):
        """
            Get all items from Project panel according to arguments.
            There are multiple different types:
                CompItem (could have multiple layers - source for Creator)
                FolderItem (collection type, currently not used
                FootageItem (imported file - created by Loader)
        Args:
            comps (bool): return CompItems
            folders (bool): return FolderItem
            footages (bool: return FootageItem

        Returns:
            (list) of namedtuples
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_items',
                                         comps=comps,
                                         folders=folders,
                                         footages=footages)
                                        )
        return self._to_records(res)

    def get_selected_items(self, comps, folders=False, footages=False):
        """
            Same as get_items but using selected items only
        Args:
            comps (bool): return CompItems
            folders (bool): return FolderItem
            footages (bool: return FootageItem

        Returns:
            (list) of namedtuples

        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_selected_items',
                                         comps=comps,
                                         folders=folders,
                                         footages=footages)
                                        )
        return self._to_records(res)

    def import_file(self, path, item_name, import_options=None):
        """
            Imports file as a FootageItem. Used in Loader
        Args:
            path (string): absolute path for asset file
            item_name (string): label for created FootageItem
            import_options (dict): different files (img vs psd) need different
                config

        """
        res = self.websocketserver.call(self.client.call(
                'AfterEffects.import_file',
                path=path,
                item_name=item_name,
                import_options=import_options)
              )
        records = self._to_records(res)
        if records:
            return records.pop()

        log.debug("Couldn't import {} file".format(path))

    def replace_item(self, item, path, item_name):
        """ Replace FootageItem with new file

            Args:
                item (dict):
                path (string):absolute path
                item_name (string): label on item in Project list

        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.replace_item',
                                   item_id=item.id,
                                   path=path, item_name=item_name))

    def rename_item(self, item, item_name):
        """ Replace item with item_name

            Args:
                item (dict):
                item_name (string): label on item in Project list

        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.rename_item',
                                   item_id=item.id,
                                   item_name=item_name))

    def delete_item(self, item):
        """ Deletes FootageItem with new file
            Args:
                item (dict):

        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.delete_item',
                                   item_id=item.id
                                   ))

    def is_saved(self):
        # TODO
        return True

    def set_label_color(self, item_id, color_idx):
        """
            Used for highlight additional information in Project panel.
            Green color is loaded asset, blue is created asset
        Args:
            item_id (int):
            color_idx (int): 0-16 Label colors from AE Project view
        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.set_label_color',
                                   item_id=item_id,
                                   color_idx=color_idx
                                   ))

    def get_work_area(self, item_id):
        """ Get work are information for render purposes
            Args:
                item_id (int):

            Returns:
                (namedtuple)

        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_work_area',
                                         item_id=item_id
                                         ))

        records = self._to_records(res)
        if records:
            return records.pop()

        log.debug("Couldn't get work area")

    def set_work_area(self, item, start, duration, frame_rate):
        """
            Set work area to predefined values (from Ftrack).
            Work area directs what gets rendered.
            Beware of rounding, AE expects seconds, not frames directly.

        Args:
            item (dict):
            start (float): workAreaStart in seconds
            duration (float): in seconds
            frame_rate (float): frames in seconds
        """
        self.websocketserver.call(self.client.call
                                  ('AfterEffects.set_work_area',
                                   item_id=item.id,
                                   start=start,
                                   duration=duration,
                                   frame_rate=frame_rate
                                   ))

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

    def get_render_info(self):
        """ Get render queue info for render purposes

            Returns:
                (namedtuple): with 'file_name' field
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_render_info'))

        records = self._to_records(res)
        if records:
            return records.pop()

        log.debug("Couldn't get render queue info")

    def get_audio_url(self, item_id):
        """ Get audio layer absolute url for comp

            Args:
                item_id (int): composition id
            Returns:
                (str): absolute path url
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_audio_url',
                                         item_id=item_id))

        return res

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
