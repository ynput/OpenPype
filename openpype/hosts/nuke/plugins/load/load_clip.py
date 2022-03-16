import nuke
import qargparse
from avalon import api, io

from openpype.hosts.nuke.api.lib import (
    get_imageio_input_colorspace,
    maintained_selection
)
from openpype.hosts.nuke.api import (
    containerise,
    update_container,
    viewer_update_and_undo_stop,
    colorspace_exists_on_node
)
from openpype.hosts.nuke.api import plugin


class LoadClip(plugin.NukeLoader):
    """Load clip into Nuke

    Either it is image sequence or video file.
    """

    families = [
        "source",
        "plate",
        "render",
        "prerender",
        "review"
    ]
    representations = [
        "exr",
        "dpx",
        "mov",
        "review",
        "mp4"
    ]

    label = "Load Clip"
    order = -20
    icon = "file-video-o"
    color = "white"

    script_start = int(nuke.root()["first_frame"].value())

    # option gui
    defaults = {
        "start_at_workfile": True
    }

    options = [
        qargparse.Boolean(
            "start_at_workfile",
            help="Load at workfile start frame",
            default=True
        )
    ]

    node_name_template = "{class_name}_{ext}"

    @classmethod
    def get_representations(cls):
        return (
            cls.representations
            + cls._representations
            + plugin.get_review_presets_config()
        )

    def load(self, context, name, namespace, options):
        repre = context["representation"]
        # reste container id so it is always unique for each instance
        self.reset_container_id()

        is_sequence = len(repre["files"]) > 1

        file = self.fname.replace("\\", "/")

        start_at_workfile = options.get(
            "start_at_workfile", self.defaults["start_at_workfile"])

        version = context['version']
        version_data = version.get("data", {})
        repre_id = repre["_id"]

        repre_cont = repre["context"]

        self.log.info("version_data: {}\n".format(version_data))
        self.log.debug(
            "Representation id `{}` ".format(repre_id))

        self.handle_start = version_data.get("handleStart", 0)
        self.handle_end = version_data.get("handleEnd", 0)

        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        first -= self.handle_start
        last += self.handle_end

        if not is_sequence:
            duration = last - first
            first = 1
            last = first + duration
        elif "#" not in file:
            frame = repre_cont.get("frame")
            assert frame, "Representation is not sequence"

            padding = len(frame)
            file = file.replace(frame, "#" * padding)

        # Fallback to asset name when namespace is None
        if namespace is None:
            namespace = context['asset']['name']

        if not file:
            self.log.warning(
                "Representation id `{}` is failing to load".format(repre_id))
            return

        read_name = self._get_node_name(repre)

        # Create the Loader with the filename path set
        read_node = nuke.createNode(
            "Read",
            "name {}".format(read_name))

        # to avoid multiple undo steps for rest of process
        # we will switch off undo-ing
        with viewer_update_and_undo_stop():
            read_node["file"].setValue(file)

            used_colorspace = self._set_colorspace(
                read_node, version_data, repre["data"])

            self._set_range_to_node(read_node, first, last, start_at_workfile)

            # add additional metadata from the version to imprint Avalon knob
            add_keys = ["frameStart", "frameEnd",
                        "source", "colorspace", "author", "fps", "version",
                        "handleStart", "handleEnd"]

            data_imprint = {}
            for k in add_keys:
                if k == 'version':
                    data_imprint.update({k: context["version"]['name']})
                elif k == 'colorspace':
                    colorspace = repre["data"].get(k)
                    colorspace = colorspace or version_data.get(k)
                    data_imprint["db_colorspace"] = colorspace
                    if used_colorspace:
                        data_imprint["used_colorspace"] = used_colorspace
                else:
                    data_imprint.update(
                        {k: context["version"]['data'].get(k, str(None))})

            data_imprint.update({"objectName": read_name})

            read_node["tile_color"].setValue(int("0x4ecd25ff", 16))

            container = containerise(
                read_node,
                name=name,
                namespace=namespace,
                context=context,
                loader=self.__class__.__name__,
                data=data_imprint)

        if version_data.get("retime", None):
            self._make_retimes(read_node, version_data)

        self.set_as_member(read_node)

        return container

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """Update the Loader's path

        Nuke automatically tries to reset some variables when changing
        the loader's path to a new file. These automatic changes are to its
        inputs:

        """

        is_sequence = len(representation["files"]) > 1

        read_node = nuke.toNode(container['objectName'])
        file = api.get_representation_path(representation).replace("\\", "/")

        start_at_workfile = bool("start at" in read_node['frame_mode'].value())

        version = io.find_one({
            "type": "version",
            "_id": representation["parent"]
        })
        version_data = version.get("data", {})
        repre_id = representation["_id"]

        repre_cont = representation["context"]

        # colorspace profile
        colorspace = representation["data"].get("colorspace")
        colorspace = colorspace or version_data.get("colorspace")

        self.handle_start = version_data.get("handleStart", 0)
        self.handle_end = version_data.get("handleEnd", 0)

        first = version_data.get("frameStart", None)
        last = version_data.get("frameEnd", None)
        first -= self.handle_start
        last += self.handle_end

        if not is_sequence:
            duration = last - first
            first = 1
            last = first + duration
        elif "#" not in file:
            frame = repre_cont.get("frame")
            assert frame, "Representation is not sequence"

            padding = len(frame)
            file = file.replace(frame, "#" * padding)

        if not file:
            self.log.warning(
                "Representation id `{}` is failing to load".format(repre_id))
            return

        read_name = self._get_node_name(representation)

        read_node["name"].setValue(read_name)
        read_node["file"].setValue(file)

        # to avoid multiple undo steps for rest of process
        # we will switch off undo-ing
        with viewer_update_and_undo_stop():
            used_colorspace = self._set_colorspace(
                read_node, version_data, representation["data"],
                path=file)

            self._set_range_to_node(read_node, first, last, start_at_workfile)

            updated_dict = {
                "representation": str(representation["_id"]),
                "frameStart": str(first),
                "frameEnd": str(last),
                "version": str(version.get("name")),
                "db_colorspace": colorspace,
                "source": version_data.get("source"),
                "handleStart": str(self.handle_start),
                "handleEnd": str(self.handle_end),
                "fps": str(version_data.get("fps")),
                "author": version_data.get("author")
            }

            # add used colorspace if found any
            if used_colorspace:
                updated_dict["used_colorspace"] = used_colorspace

            # change color of read_node
            # get all versions in list
            versions = io.find({
                "type": "version",
                "parent": version["parent"]
            }).distinct('name')

            max_version = max(versions)

            if version.get("name") not in [max_version]:
                read_node["tile_color"].setValue(int("0xd84f20ff", 16))
            else:
                read_node["tile_color"].setValue(int("0x4ecd25ff", 16))

            # Update the imprinted representation
            update_container(
                read_node,
                updated_dict
            )
            self.log.info("updated to version: {}".format(version.get("name")))

        if version_data.get("retime", None):
            self._make_retimes(read_node, version_data)
        else:
            self.clear_members(read_node)

        self.set_as_member(read_node)

    def remove(self, container):
        read_node = nuke.toNode(container['objectName'])
        assert read_node.Class() == "Read", "Must be Read"

        with viewer_update_and_undo_stop():
            members = self.get_members(read_node)
            nuke.delete(read_node)
            for member in members:
                nuke.delete(member)

    def _set_range_to_node(self, read_node, first, last, start_at_workfile):
        read_node['origfirst'].setValue(int(first))
        read_node['first'].setValue(int(first))
        read_node['origlast'].setValue(int(last))
        read_node['last'].setValue(int(last))

        # set start frame depending on workfile or version
        self._loader_shift(read_node, start_at_workfile)

    def _make_retimes(self, parent_node, version_data):
        ''' Create all retime and timewarping nodes with copied animation '''
        speed = version_data.get('speed', 1)
        time_warp_nodes = version_data.get('timewarps', [])
        last_node = None
        source_id = self.get_container_id(parent_node)
        self.log.info("__ source_id: {}".format(source_id))
        self.log.info("__ members: {}".format(self.get_members(parent_node)))
        dependent_nodes = self.clear_members(parent_node)

        with maintained_selection():
            parent_node['selected'].setValue(True)

            if speed != 1:
                rtn = nuke.createNode(
                    "Retime",
                    "speed {}".format(speed))

                rtn["before"].setValue("continue")
                rtn["after"].setValue("continue")
                rtn["input.first_lock"].setValue(True)
                rtn["input.first"].setValue(
                    self.script_start
                )
                self.set_as_member(rtn)
                last_node = rtn

            if time_warp_nodes != []:
                start_anim = self.script_start + (self.handle_start / speed)
                for timewarp in time_warp_nodes:
                    twn = nuke.createNode(
                        timewarp["Class"],
                        "name {}".format(timewarp["name"])
                    )
                    if isinstance(timewarp["lookup"], list):
                        # if array for animation
                        twn["lookup"].setAnimated()
                        for i, value in enumerate(timewarp["lookup"]):
                            twn["lookup"].setValueAt(
                                (start_anim + i) + value,
                                (start_anim + i))
                    else:
                        # if static value `int`
                        twn["lookup"].setValue(timewarp["lookup"])

                    self.set_as_member(twn)
                    last_node = twn

            if dependent_nodes:
                # connect to original inputs
                for i, n in enumerate(dependent_nodes):
                    last_node.setInput(i, n)

    def _loader_shift(self, read_node, workfile_start=False):
        """ Set start frame of read node to a workfile start

        Args:
            read_node (nuke.Node): The nuke's read node
            workfile_start (bool): set workfile start frame if true

        """
        if workfile_start:
            read_node['frame_mode'].setValue("start at")
            read_node['frame'].setValue(str(self.script_start))

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

    def _set_colorspace(self, node, version_data, repre_data, path=None):
        output_color = None
        path = path or self.fname.replace("\\", "/")
        # get colorspace
        colorspace = repre_data.get("colorspace")
        colorspace = colorspace or version_data.get("colorspace")

        # colorspace from `project_anatomy/imageio/nuke/regexInputs`
        iio_colorspace = get_imageio_input_colorspace(path)

        # Set colorspace defined in version data
        if (
            colorspace is not None
            and colorspace_exists_on_node(node, str(colorspace))
        ):
            node["colorspace"].setValue(str(colorspace))
            output_color = str(colorspace)
        elif iio_colorspace is not None:
            node["colorspace"].setValue(iio_colorspace)
            output_color = iio_colorspace

        return output_color
