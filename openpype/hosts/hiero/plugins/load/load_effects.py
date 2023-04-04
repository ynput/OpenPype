import json
from collections import OrderedDict
import six

from openpype.client import (
    get_version_by_id
)

from openpype.pipeline import (
    AVALON_CONTAINER_ID,
    load,
    get_representation_path,
    get_current_project_name
)
from openpype.hosts.hiero import api as phiero
from openpype.lib import Logger


class LoadEffects(load.LoaderPlugin):
    """Loading colorspace soft effect exported from nukestudio"""

    families = ["effect"]
    representations = ["*"]
    extension = {"json"}

    label = "Load Effects"
    order = 0
    icon = "cc"
    color = "white"

    log = Logger.get_logger(__name__)

    def load(self, context, name, namespace, data):
        """
        Loading function to get the soft effects to particular read node

        Arguments:
            context (dict): context of version
            name (str): name of the version
            namespace (str): asset name
            data (dict): compulsory attribute > not used

        Returns:
            nuke node: containerised nuke node object
        """
        active_sequence = phiero.get_current_sequence()
        active_track = phiero.get_current_track(
            active_sequence, "Loaded_{}".format(name))

        # get main variables
        namespace = namespace or context["asset"]["name"]
        object_name = "{}_{}".format(name, namespace)
        clip_in = context["asset"]["data"]["clipIn"]
        clip_out = context["asset"]["data"]["clipOut"]

        data_imprint = {
            "objectName": object_name,
            "children_names": []
        }

        # getting file path
        file = self.filepath_from_context(context)
        file = file.replace("\\", "/")

        if self._shared_loading(
            file,
            active_track,
            clip_in,
            clip_out,
            data_imprint
        ):
            self.containerise(
                active_track,
                name=name,
                namespace=namespace,
                object_name=object_name,
                context=context,
                loader=self.__class__.__name__,
                data=data_imprint)

    def _shared_loading(
        self,
        file,
        active_track,
        clip_in,
        clip_out,
        data_imprint,
        update=False
    ):
        # getting data from json file with unicode conversion
        with open(file, "r") as f:
            json_f = {self.byteify(key): self.byteify(value)
                      for key, value in json.load(f).items()}

        # get correct order of nodes by positions on track and subtrack
        nodes_order = self.reorder_nodes(json_f)

        used_subtracks = {
            stitem.name(): stitem
            for stitem in phiero.flatten(active_track.subTrackItems())
        }

        loaded = False
        for index_order, (ef_name, ef_val) in enumerate(nodes_order.items()):
            new_name = "{}_loaded".format(ef_name)
            if new_name not in used_subtracks:
                effect_track_item = active_track.createEffect(
                    effectType=ef_val["class"],
                    timelineIn=clip_in,
                    timelineOut=clip_out,
                    subTrackIndex=index_order

                )
                effect_track_item.setName(new_name)
            else:
                effect_track_item = used_subtracks[new_name]

            node = effect_track_item.node()
            for knob_name, knob_value in ef_val["node"].items():
                if (
                    not knob_value
                    or knob_name == "name"
                ):
                    continue

                try:
                    # assume list means animation
                    # except 4 values could be RGBA or vector
                    if isinstance(knob_value, list) and len(knob_value) > 4:
                        node[knob_name].setAnimated()
                        for i, value in enumerate(knob_value):
                            if isinstance(value, list):
                                # list can have vector animation
                                for ci, cv in enumerate(value):
                                    node[knob_name].setValueAt(
                                        cv,
                                        (clip_in + i),
                                        ci
                                    )
                            else:
                                # list is single values
                                node[knob_name].setValueAt(
                                    value,
                                    (clip_in + i)
                                )
                    else:
                        node[knob_name].setValue(knob_value)
                except NameError:
                    self.log.warning("Knob: {} cannot be set".format(
                        knob_name))

            # register all loaded children
            data_imprint["children_names"].append(new_name)

            # make sure containerisation will happen
            loaded = True

        return loaded

    def update(self, container, representation):
        """ Updating previously loaded effects
        """
        active_track = container["_item"]
        file = get_representation_path(representation).replace("\\", "/")

        # get main variables
        name = container['name']
        namespace = container['namespace']

        # get timeline in out data
        project_name = get_current_project_name()
        version_doc = get_version_by_id(project_name, representation["parent"])
        version_data = version_doc["data"]
        clip_in = version_data["clipIn"]
        clip_out = version_data["clipOut"]

        object_name = "{}_{}".format(name, namespace)

        # Disable previously created nodes
        used_subtracks = {
            stitem.name(): stitem
            for stitem in phiero.flatten(active_track.subTrackItems())
        }
        container = phiero.get_track_openpype_data(
            active_track, object_name
        )

        loaded_subtrack_items = container["children_names"]
        for loaded_stitem in loaded_subtrack_items:
            if loaded_stitem not in used_subtracks:
                continue
            item_to_remove = used_subtracks.pop(loaded_stitem)
            # TODO: find a way to erase nodes
            self.log.debug(
                "This node needs to be removed: {}".format(item_to_remove))

        data_imprint = {
            "objectName": object_name,
            "name": name,
            "representation": str(representation["_id"]),
            "children_names": []
        }

        if self._shared_loading(
            file,
            active_track,
            clip_in,
            clip_out,
            data_imprint,
            update=True
        ):
            return phiero.update_container(active_track, data_imprint)

    def reorder_nodes(self, data):
        new_order = OrderedDict()
        trackNums = [v["trackIndex"] for k, v in data.items()
                     if isinstance(v, dict)]
        subTrackNums = [v["subTrackIndex"] for k, v in data.items()
                        if isinstance(v, dict)]

        for trackIndex in range(
                min(trackNums), max(trackNums) + 1):
            for subTrackIndex in range(
                    min(subTrackNums), max(subTrackNums) + 1):
                item = self.get_item(data, trackIndex, subTrackIndex)
                if item is not {}:
                    new_order.update(item)
        return new_order

    def get_item(self, data, trackIndex, subTrackIndex):
        return {key: val for key, val in data.items()
                if isinstance(val, dict)
                if subTrackIndex == val["subTrackIndex"]
                if trackIndex == val["trackIndex"]}

    def byteify(self, input):
        """
        Converts unicode strings to strings
        It goes through all dictionary

        Arguments:
            input (dict/str): input

        Returns:
            dict: with fixed values and keys

        """

        if isinstance(input, dict):
            return {self.byteify(key): self.byteify(value)
                    for key, value in input.items()}
        elif isinstance(input, list):
            return [self.byteify(element) for element in input]
        elif isinstance(input, six.text_type):
            return str(input)
        else:
            return input

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        pass

    def containerise(
        self,
        track,
        name,
        namespace,
        object_name,
        context,
        loader=None,
        data=None
    ):
        """Bundle Hiero's object into an assembly and imprint it with metadata

        Containerisation enables a tracking of version, author and origin
        for loaded assets.

        Arguments:
            track (hiero.core.VideoTrack): object to imprint as container
            name (str): Name of resulting assembly
            namespace (str): Namespace under which to host container
            object_name (str): name of container
            context (dict): Asset information
            loader (str, optional): Name of node used to produce this
                                    container.

        Returns:
            track_item (hiero.core.TrackItem): containerised object

        """

        data_imprint = {
            object_name: {
                "schema": "openpype:container-2.0",
                "id": AVALON_CONTAINER_ID,
                "name": str(name),
                "namespace": str(namespace),
                "loader": str(loader),
                "representation": str(context["representation"]["_id"]),
            }
        }

        if data:
            for k, v in data.items():
                data_imprint[object_name].update({k: v})

        self.log.debug("_ data_imprint: {}".format(data_imprint))
        phiero.set_track_openpype_tag(track, data_imprint)
