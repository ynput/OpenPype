"""
    Stub handling connection from server to client.
    Used anywhere solution is calling client methods.
"""
import json
import logging

import attr

from wsrpc_aiohttp import WebSocketAsync
from openpype.tools.adobe_webserver.app import WebServerTool


@attr.s
class AEItem(object):
    """
        Object denoting Item in AE. Each item is created in AE by any Loader,
        but contains same fields, which are being used in later processing.
    """
    # metadata
    id = attr.ib()  # id created by AE, could be used for querying
    name = attr.ib()  # name of item
    item_type = attr.ib(default=None)  # item type (footage, folder, comp)
    # all imported elements, single for
    # regular image, array for Backgrounds
    members = attr.ib(factory=list)
    workAreaStart = attr.ib(default=None)
    workAreaDuration = attr.ib(default=None)
    frameRate = attr.ib(default=None)
    file_name = attr.ib(default=None)
    instance_id = attr.ib(default=None)  # New Publisher
    width = attr.ib(default=None)
    height = attr.ib(default=None)


class AfterEffectsServerStub():
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
        self.log = logging.getLogger(self.__class__.__name__)

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
        """
            Open file located at 'path' (local).
        Args:
            path(string): file path locally
        Returns: None
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.open', path=path))

        return self._handle_return(res)

    def get_metadata(self):
        """
            Get complete stored JSON with metadata from AE.Metadata.Label
            field.

            It contains containers loaded by any Loader OR instances creted
            by Creator.

        Returns:
            (list)
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_metadata'))
        metadata = self._handle_return(res)

        return metadata or []

    def read(self, item, layers_meta=None):
        """
            Parses item metadata from Label field of active document.
            Used as filter to pick metadata for specific 'item' only.

        Args:
            item (AEItem): pulled info from AE
            layers_meta (dict): full list from Headline
                (load and inject for better performance in loops)
        Returns:
            (dict):
        """
        if layers_meta is None:
            layers_meta = self.get_metadata()
        for item_meta in layers_meta:
            if 'container' in item_meta.get('id') and \
                    str(item.id) == str(item_meta.get('members')[0]):
                return item_meta

        self.log.debug("Couldn't find layer metadata")

    def imprint(self, item_id, data, all_items=None, items_meta=None):
        """
            Save item metadata to Label field of metadata of active document
        Args:
            item_id (int|str): id of FootageItem or instance_id for workfiles
            data(string): json representation for single layer
            all_items (list of item): for performance, could be
                injected for usage in loop, if not, single call will be
                triggered
            items_meta(string): json representation from Headline
                           (for performance - provide only if imprint is in
                           loop - value should be same)
        Returns: None
        """
        if not items_meta:
            items_meta = self.get_metadata()

        result_meta = []
        # fix existing
        is_new = True

        for item_meta in items_meta:
            if ((item_meta.get('members') and
                    str(item_id) == str(item_meta.get('members')[0])) or
                    item_meta.get("instance_id") == item_id):
                is_new = False
                if data:
                    item_meta.update(data)
                    result_meta.append(item_meta)
            else:
                result_meta.append(item_meta)

        if is_new:
            result_meta.append(data)

        # Ensure only valid ids are stored.
        if not all_items:
            # loaders create FootageItem now
            all_items = self.get_items(comps=True,
                                       folders=True,
                                       footages=True)
        item_ids = [int(item.id) for item in all_items]
        cleaned_data = []
        for meta in result_meta:
            # do not added instance with nonexistend item id
            if meta.get("members"):
                if int(meta["members"][0]) not in item_ids:
                    continue

            cleaned_data.append(meta)

        payload = json.dumps(cleaned_data, indent=4)

        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.imprint',
                                         payload=payload))
        return self._handle_return(res)

    def get_active_document_full_name(self):
        """
            Returns absolute path of active document via ws call
        Returns(string): file name
        """
        res = self.websocketserver.call(self.client.call(
            'AfterEffects.get_active_document_full_name'))

        return self._handle_return(res)

    def get_active_document_name(self):
        """
            Returns just a name of active document via ws call
        Returns(string): file name
        """
        res = self.websocketserver.call(self.client.call(
            'AfterEffects.get_active_document_name'))

        return self._handle_return(res)

    def get_items(self, comps, folders=False, footages=False):
        """
            Get all items from Project panel according to arguments.
            There are multiple different types:
                CompItem (could have multiple layers - source for Creator,
                    will be rendered)
                FolderItem (collection type, currently used for Background
                    loading)
                FootageItem (imported file - created by Loader)
        Args:
            comps (bool): return CompItems
            folders (bool): return FolderItem
            footages (bool: return FootageItem

        Returns:
            (list) of namedtuples
        """
        res = self.websocketserver.call(
            self.client.call('AfterEffects.get_items',
                             comps=comps,
                             folders=folders,
                             footages=footages)
              )
        return self._to_records(self._handle_return(res))

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
        return self._to_records(self._handle_return(res))

    def get_item(self, item_id):
        """
            Returns metadata for particular 'item_id' or None

            Args:
                item_id (int, or string)
        """
        for item in self.get_items(True, True, True):
            if str(item.id) == str(item_id):
                return item

        return None

    def import_file(self, path, item_name, import_options=None):
        """
            Imports file as a FootageItem. Used in Loader
        Args:
            path (string): absolute path for asset file
            item_name (string): label for created FootageItem
            import_options (dict): different files (img vs psd) need different
                config

        """
        res = self.websocketserver.call(
            self.client.call('AfterEffects.import_file',
                             path=path,
                             item_name=item_name,
                             import_options=import_options)
            )
        records = self._to_records(self._handle_return(res))
        if records:
            return records.pop()

    def replace_item(self, item_id, path, item_name):
        """ Replace FootageItem with new file

            Args:
                item_id (int):
                path (string):absolute path
                item_name (string): label on item in Project list

        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.replace_item',
                                         item_id=item_id,
                                         path=path, item_name=item_name))

        return self._handle_return(res)

    def rename_item(self, item_id, item_name):
        """ Replace item with item_name

            Args:
                item_id (int):
                item_name (string): label on item in Project list

        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.rename_item',
                                         item_id=item_id,
                                         item_name=item_name))

        return self._handle_return(res)

    def delete_item(self, item_id):
        """ Deletes *Item in a file
            Args:
                item_id (int):

        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.delete_item',
                                         item_id=item_id))

        return self._handle_return(res)

    def remove_instance(self, instance_id):
        """
            Removes instance with 'instance_id' from file's metadata and
            saves them.

            Keep matching item in file though.

            Args:
                instance_id(string): instance id
        """
        cleaned_data = []

        for instance in self.get_metadata():
            inst_id = instance.get("instance_id") or instance.get("uuid")
            if inst_id != instance_id:
                cleaned_data.append(instance)

        payload = json.dumps(cleaned_data, indent=4)
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.imprint',
                                         payload=payload))

        return self._handle_return(res)

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
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.set_label_color',
                                         item_id=item_id,
                                         color_idx=color_idx))

        return self._handle_return(res)

    def get_work_area(self, item_id):
        """ Get work are information for render purposes
            Args:
                item_id (int):

            Returns:
                (AEItem)

        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_work_area',
                                         item_id=item_id
                                         ))

        records = self._to_records(self._handle_return(res))
        if records:
            return records.pop()

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
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.set_work_area',
                                         item_id=item.id,
                                         start=start,
                                         duration=duration,
                                         frame_rate=frame_rate))
        return self._handle_return(res)

    def save(self):
        """
            Saves active document
        Returns: None
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.save'))

        return self._handle_return(res)

    def saveAs(self, project_path, as_copy):
        """
            Saves active project to aep (copy) or png or jpg
        Args:
            project_path(string): full local path
            as_copy: <boolean>
        Returns: None
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.saveAs',
                                         image_path=project_path,
                                         as_copy=as_copy))

        return self._handle_return(res)

    def get_render_info(self):
        """ Get render queue info for render purposes

            Returns:
                (AEItem): with 'file_name' field
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.get_render_info'))

        records = self._to_records(self._handle_return(res))
        if records:
            return records.pop()

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

        return self._handle_return(res)

    def import_background(self, comp_id, comp_name, files):
        """
            Imports backgrounds images to existing or new composition.

            If comp_id is not provided, new composition is created, basic
            values (width, heights, frameRatio) takes from first imported
            image.

            All images from background json are imported as a FootageItem and
            separate layer is created for each of them under composition.

            Order of imported 'files' is important.

            Args:
                comp_id (int): id of existing composition (null if new)
                comp_name (str): used when new composition
                files (list): list of absolute paths to import and
                add as layers

            Returns:
                (AEItem): object with id of created folder, all imported images
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.import_background',
                                         comp_id=comp_id,
                                         comp_name=comp_name,
                                         files=files))

        records = self._to_records(self._handle_return(res))
        if records:
            return records.pop()

    def reload_background(self, comp_id, comp_name, files):
        """
            Reloads backgrounds images to existing composition.

            It actually deletes complete folder with imported images and
            created composition for safety.

            Args:
                comp_id (int): id of existing composition to be overwritten
                comp_name (str): new name of composition (could be same as old
                    if version up only)
                files (list): list of absolute paths to import and
                    add as layers
            Returns:
                (AEItem): object with id of created folder, all imported images
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.reload_background',
                                         comp_id=comp_id,
                                         comp_name=comp_name,
                                         files=files))

        records = self._to_records(self._handle_return(res))
        if records:
            return records.pop()

    def add_item_as_layer(self, comp_id, item_id):
        """
            Adds already imported FootageItem ('item_id') as a new
            layer to composition ('comp_id').

            Args:
                comp_id (int): id of target composition
                item_id (int): FootageItem.id
                comp already found previously
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.add_item_as_layer',
                                         comp_id=comp_id,
                                         item_id=item_id))

        records = self._to_records(self._handle_return(res))
        if records:
            return records.pop()

    def render(self, folder_url):
        """
            Render all renderqueueitem to 'folder_url'
        Args:
            folder_url(string): local folder path for collecting
        Returns: None
        """
        res = self.websocketserver.call(self.client.call
                                        ('AfterEffects.render',
                                         folder_url=folder_url))
        return self._handle_return(res)

    def get_extension_version(self):
        """Returns version number of installed extension."""
        res = self.websocketserver.call(self.client.call(
            'AfterEffects.get_extension_version'))

        return self._handle_return(res)

    def get_app_version(self):
        """Returns version number of installed application (17.5...)."""
        res = self.websocketserver.call(self.client.call(
            'AfterEffects.get_app_version'))

        return self._handle_return(res)

    def close(self):
        res = self.websocketserver.call(self.client.call('AfterEffects.close'))

        return self._handle_return(res)

    def _handle_return(self, res):
        """Wraps return, throws ValueError if 'error' key is present."""
        if res and isinstance(res, str) and res != "undefined":
            try:
                parsed = json.loads(res)
            except json.decoder.JSONDecodeError:
                raise ValueError("Received broken JSON {}".format(res))

            if not parsed:  # empty list
                return parsed

            first_item = parsed
            if isinstance(parsed, list):
                first_item = parsed[0]

            if first_item:
                if first_item.get("error"):
                    raise ValueError(first_item["error"])
                # singular values (file name etc)
                if first_item.get("result") is not None:
                    return first_item["result"]
            return parsed  # parsed
        return res

    def _to_records(self, payload):
        """
            Converts string json representation into list of AEItem
            dot notation access to work.
        Returns: <list of AEItem>
            payload(dict): - dictionary from json representation, expected to
                come from _handle_return
        """
        if not payload:
            return []

        if isinstance(payload, str):  # safety fallback
            try:
                payload = json.loads(payload)
            except json.decoder.JSONDecodeError:
                raise ValueError("Received broken JSON {}".format(payload))

        if isinstance(payload, dict):
            payload = [payload]

        ret = []
        # convert to AEItem to use dot donation
        for d in payload:
            if not d:
                continue
            # currently implemented and expected fields
            item = AEItem(d.get('id'),
                          d.get('name'),
                          d.get('type'),
                          d.get('members'),
                          d.get('workAreaStart'),
                          d.get('workAreaDuration'),
                          d.get('frameRate'),
                          d.get('file_name'),
                          d.get("instance_id"),
                          d.get("width"),
                          d.get("height"))

            ret.append(item)
        return ret
