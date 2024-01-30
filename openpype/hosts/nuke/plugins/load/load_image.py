import nuke

import qargparse

from openpype.client import (
    get_version_by_id,
    get_last_version_by_subset_id,
)
from openpype.pipeline import (
    load,
    get_current_project_name,
    get_representation_path,
)
from openpype.hosts.nuke.api.lib import (
    get_imageio_input_colorspace
)
from openpype.hosts.nuke.api import (
    containerise,
    update_container,
    viewer_update_and_undo_stop
)
from openpype.lib.transcoding import (
    IMAGE_EXTENSIONS
)


class LoadImage(load.LoaderPlugin):
    """Load still image into Nuke"""

    families = [
        "render2d",
        "source",
        "plate",
        "render",
        "prerender",
        "review",
        "image"
    ]
    representations = ["*"]
    extensions = set(
        ext.lstrip(".") for ext in IMAGE_EXTENSIONS
    )

    label = "Load Image"
    order = -10
    icon = "image"
    color = "white"

    # Loaded from settings
    _representations = []

    node_name_template = "{class_name}_{ext}"

    options = [
        qargparse.Integer(
            "frame_number",
            label="Frame Number",
            default=int(nuke.root()["first_frame"].getValue()),
            min=1,
            max=999999,
            help="What frame is reading from?"
        )
    ]

    @classmethod
    def get_representations(cls):
        return cls._representations or cls.representations

    def load(self, context, name, namespace, options):
        self.log.info("__ options: `{}`".format(options))
        frame_number = options.get(
            "frame_number", int(nuke.root()["first_frame"].getValue())
        )

        version = context['version']
        version_data = version.get("data", {})
        repr_id = context["representation"]["_id"]

        self.log.info("version_data: {}\n".format(version_data))
        self.log.debug(
            "Representation id `{}` ".format(repr_id))

        last = first = int(frame_number)

        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        file = self.filepath_from_context(context)

        if not file:
            repr_id = context["representation"]["_id"]
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = file.replace("\\", "/")

        representation = context["representation"]
        repr_cont = representation["context"]
        frame = repr_cont.get("frame")
        if frame:
            padding = len(frame)
            file = file.replace(
                frame,
                format(frame_number, "0{}".format(padding)))

        read_name = self._get_node_name(representation)

        # Create the Loader with the filename path set
        with viewer_update_and_undo_stop():
            r = nuke.createNode(
                "Read",
                "name {}".format(read_name),
                inpanel=False
            )

            r["file"].setValue(file)

            # Set colorspace defined in version data
            colorspace = context["version"]["data"].get("colorspace")
            if colorspace:
                r["colorspace"].setValue(str(colorspace))

            preset_clrsp = get_imageio_input_colorspace(file)

            if preset_clrsp is not None:
                r["colorspace"].setValue(preset_clrsp)

            r["origfirst"].setValue(first)
            r["first"].setValue(first)
            r["origlast"].setValue(last)
            r["last"].setValue(last)

            # add additional metadata from the version to imprint Avalon knob
            add_keys = ["source", "colorspace", "author", "fps", "version"]

            data_imprint = {
                "frameStart": first,
                "frameEnd": last
            }
            for k in add_keys:
                if k == 'version':
                    data_imprint.update({k: context["version"]['name']})
                else:
                    data_imprint.update(
                        {k: context["version"]['data'].get(k, str(None))})

            r["tile_color"].setValue(int("0x4ecd25ff", 16))

            return containerise(r,
                                name=name,
                                namespace=namespace,
                                context=context,
                                loader=self.__class__.__name__,
                                data=data_imprint)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """Update the Loader's path

        Nuke automatically tries to reset some variables when changing
        the loader's path to a new file. These automatic changes are to its
        inputs:

        """
        node = container["node"]
        frame_number = node["first"].value()

        assert node.Class() == "Read", "Must be Read"

        repr_cont = representation["context"]

        file = get_representation_path(representation)

        if not file:
            repr_id = representation["_id"]
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = file.replace("\\", "/")

        frame = repr_cont.get("frame")
        if frame:
            padding = len(frame)
            file = file.replace(
                frame,
                format(frame_number, "0{}".format(padding)))

        # Get start frame from version data
        project_name = get_current_project_name()
        version_doc = get_version_by_id(project_name, representation["parent"])
        last_version_doc = get_last_version_by_subset_id(
            project_name, version_doc["parent"], fields=["_id"]
        )

        version_data = version_doc.get("data", {})

        last = first = int(frame_number)

        # Set the global in to the start frame of the sequence
        node["file"].setValue(file)
        node["origfirst"].setValue(first)
        node["first"].setValue(first)
        node["origlast"].setValue(last)
        node["last"].setValue(last)

        updated_dict = {}
        updated_dict.update({
            "representation": str(representation["_id"]),
            "frameStart": str(first),
            "frameEnd": str(last),
            "version": str(version_doc.get("name")),
            "colorspace": version_data.get("colorspace"),
            "source": version_data.get("source"),
            "fps": str(version_data.get("fps")),
            "author": version_data.get("author")
        })

        # change color of node
        if version_doc["_id"] == last_version_doc["_id"]:
            color_value = "0x4ecd25ff"
        else:
            color_value = "0xd84f20ff"
        node["tile_color"].setValue(int(color_value, 16))

        # Update the imprinted representation
        update_container(
            node,
            updated_dict
        )
        self.log.info("updated to version: {}".format(version_doc.get("name")))

    def remove(self, container):
        node = container["node"]
        assert node.Class() == "Read", "Must be Read"

        with viewer_update_and_undo_stop():
            nuke.delete(node)

    def _get_node_name(self, representation):

        repre_cont = representation["context"]
        name_data = {
            "asset": repre_cont["asset"],
            "subset": repre_cont["subset"],
            "representation": representation["name"],
            "ext": repre_cont["representation"],
            "id": representation["_id"],
            "class_name": self.__class__.__name__
        }

        return self.node_name_template.format(**name_data)
