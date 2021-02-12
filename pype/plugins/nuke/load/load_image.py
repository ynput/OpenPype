import re
import nuke

from avalon.vendor import qargparse
from avalon import api, io

from pype.hosts.nuke import presets


class LoadImage(api.Loader):
    """Load still image into Nuke"""

    families = [
        "render2d", "source", "plate",
        "render", "prerender", "review",
        "image"
    ]
    representations = ["exr", "dpx", "jpg", "jpeg", "png", "psd"]

    label = "Load Image"
    order = -10
    icon = "image"
    color = "white"

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

    def load(self, context, name, namespace, options):
        from avalon.nuke import (
            containerise,
            viewer_update_and_undo_stop
        )
        self.log.info("__ options: `{}`".format(options))
        frame_number = options.get("frame_number", 1)

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

        file = self.fname

        if not file:
            repr_id = context["representation"]["_id"]
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        file = file.replace("\\", "/")

        repr_cont = context["representation"]["context"]
        frame = repr_cont.get("frame")
        if frame:
            padding = len(frame)
            file = file.replace(
                frame,
                format(frame_number, "0{}".format(padding)))

        read_name = "Read_{0}_{1}_{2}".format(
            repr_cont["asset"],
            repr_cont["subset"],
            repr_cont["representation"])

        # Create the Loader with the filename path set
        with viewer_update_and_undo_stop():
            r = nuke.createNode(
                "Read",
                "name {}".format(read_name))
            r["file"].setValue(file)

            # Set colorspace defined in version data
            colorspace = context["version"]["data"].get("colorspace")
            if colorspace:
                r["colorspace"].setValue(str(colorspace))

            # load nuke presets for Read's colorspace
            read_clrs_presets = presets.get_colorspace_preset().get(
                "nuke", {}).get("read", {})

            # check if any colorspace presets for read is mathing
            preset_clrsp = next((read_clrs_presets[k]
                                 for k in read_clrs_presets
                                 if bool(re.search(k, file))),
                                None)
            if preset_clrsp is not None:
                r["colorspace"].setValue(str(preset_clrsp))

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

            data_imprint.update({"objectName": read_name})

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

        from avalon.nuke import (
            update_container
        )

        node = nuke.toNode(container["objectName"])
        frame_number = node["first"].value()

        assert node.Class() == "Read", "Must be Read"

        repr_cont = representation["context"]

        file = api.get_representation_path(representation)

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
        version = io.find_one({
            "type": "version",
            "_id": representation["parent"]
        })

        # get all versions in list
        versions = io.find({
            "type": "version",
            "parent": version["parent"]
        }).distinct('name')

        max_version = max(versions)

        version_data = version.get("data", {})

        last = first = int(frame_number)

        # Set the global in to the start frame of the sequence
        node["origfirst"].setValue(first)
        node["first"].setValue(first)
        node["origlast"].setValue(last)
        node["last"].setValue(last)

        updated_dict = {}
        updated_dict.update({
            "representation": str(representation["_id"]),
            "frameStart": str(first),
            "frameEnd": str(last),
            "version": str(version.get("name")),
            "colorspace": version_data.get("colorspace"),
            "source": version_data.get("source"),
            "fps": str(version_data.get("fps")),
            "author": version_data.get("author"),
            "outputDir": version_data.get("outputDir"),
        })

        # change color of node
        if version.get("name") not in [max_version]:
            node["tile_color"].setValue(int("0xd84f20ff", 16))
        else:
            node["tile_color"].setValue(int("0x4ecd25ff", 16))

        # Update the imprinted representation
        update_container(
            node,
            updated_dict
        )
        self.log.info("udated to version: {}".format(version.get("name")))

    def remove(self, container):

        from avalon.nuke import viewer_update_and_undo_stop

        node = nuke.toNode(container['objectName'])
        assert node.Class() == "Read", "Must be Read"

        with viewer_update_and_undo_stop():
            nuke.delete(node)
