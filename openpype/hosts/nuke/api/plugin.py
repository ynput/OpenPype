import os
import random
import string
from collections import OrderedDict
from abc import abstractmethod

import nuke

from openpype.api import get_current_project_settings
from openpype.pipeline import (
    LegacyCreator,
    LoaderPlugin,
)
from .lib import (
    Knobby,
    check_subsetname_exists,
    reset_selection,
    maintained_selection,
    set_avalon_knob_data,
    add_publish_knob
)


class OpenPypeCreator(LegacyCreator):
    """Pype Nuke Creator class wrapper"""
    node_color = "0xdfea5dff"

    def __init__(self, *args, **kwargs):
        super(OpenPypeCreator, self).__init__(*args, **kwargs)
        self.presets = get_current_project_settings()["nuke"]["create"].get(
            self.__class__.__name__, {}
        )
        if check_subsetname_exists(
                nuke.allNodes(),
                self.data["subset"]):
            msg = ("The subset name `{0}` is already used on a node in"
                   "this workfile.".format(self.data["subset"]))
            self.log.error(msg + "\n\nPlease use other subset name!")
            raise NameError("`{0}: {1}".format(__name__, msg))
        return

    def process(self):
        from nukescripts import autoBackdrop

        instance = None

        if (self.options or {}).get("useSelection"):

            nodes = nuke.selectedNodes()
            if not nodes:
                nuke.message("Please select nodes that you "
                             "wish to add to a container")
                return

            elif len(nodes) == 1:
                # only one node is selected
                instance = nodes[0]

        if not instance:
            # Not using selection or multiple nodes selected
            bckd_node = autoBackdrop()
            bckd_node["tile_color"].setValue(int(self.node_color, 16))
            bckd_node["note_font_size"].setValue(24)
            bckd_node["label"].setValue("[{}]".format(self.name))

            instance = bckd_node

        # add avalon knobs
        set_avalon_knob_data(instance, self.data)
        add_publish_knob(instance)

        return instance


def get_review_presets_config():
    settings = get_current_project_settings()
    review_profiles = (
        settings["global"]
        ["publish"]
        ["ExtractReview"]
        ["profiles"]
    )

    outputs = {}
    for profile in review_profiles:
        outputs.update(profile.get("outputs", {}))

    return [str(name) for name, _prop in outputs.items()]


class NukeLoader(LoaderPlugin):
    container_id_knob = "containerId"
    container_id = None

    def reset_container_id(self):
        self.container_id = "".join(random.choice(
            string.ascii_uppercase + string.digits) for _ in range(10))

    def get_container_id(self, node):
        id_knob = node.knobs().get(self.container_id_knob)
        return id_knob.value() if id_knob else None

    def get_members(self, source):
        """Return nodes that has same "containerId" as `source`"""
        source_id = self.get_container_id(source)
        return [node for node in nuke.allNodes(recurseGroups=True)
                if self.get_container_id(node) == source_id
                and node is not source] if source_id else []

    def set_as_member(self, node):
        source_id = self.get_container_id(node)

        if source_id:
            node[self.container_id_knob].setValue(source_id)
        else:
            HIDEN_FLAG = 0x00040000
            _knob = Knobby(
                "String_Knob",
                self.container_id,
                flags=[
                    nuke.READ_ONLY,
                    HIDEN_FLAG
                ])
            knob = _knob.create(self.container_id_knob)
            node.addKnob(knob)

    def clear_members(self, parent_node):
        members = self.get_members(parent_node)

        dependent_nodes = None
        for node in members:
            _depndc = [n for n in node.dependent() if n not in members]
            if not _depndc:
                continue

            dependent_nodes = _depndc
            break

        for member in members:
            self.log.info("removing node: `{}".format(member.name()))
            nuke.delete(member)

        return dependent_nodes


class ExporterReview(object):
    """
    Base class object for generating review data from Nuke

    Args:
        klass (pyblish.plugin): pyblish plugin parent
        instance (pyblish.instance): instance of pyblish context

    """
    data = None
    publish_on_farm = False

    def __init__(self,
                 klass,
                 instance,
                 multiple_presets=True
                 ):

        self.log = klass.log
        self.instance = instance
        self.multiple_presets = multiple_presets
        self.path_in = self.instance.data.get("path", None)
        self.staging_dir = self.instance.data["stagingDir"]
        self.collection = self.instance.data.get("collection", None)
        self.data = dict({
            "representations": list()
        })

    def get_file_info(self):
        if self.collection:
            self.log.debug("Collection: `{}`".format(self.collection))
            # get path
            self.fname = os.path.basename(self.collection.format(
                "{head}{padding}{tail}"))
            self.fhead = self.collection.format("{head}")

            # get first and last frame
            self.first_frame = min(self.collection.indexes)
            self.last_frame = max(self.collection.indexes)
            if "slate" in self.instance.data["families"]:
                self.first_frame += 1
        else:
            self.fname = os.path.basename(self.path_in)
            self.fhead = os.path.splitext(self.fname)[0] + "."
            self.first_frame = self.instance.data.get("frameStartHandle", None)
            self.last_frame = self.instance.data.get("frameEndHandle", None)

        if "#" in self.fhead:
            self.fhead = self.fhead.replace("#", "")[:-1]

    def get_representation_data(self, tags=None, range=False):
        add_tags = tags or []
        repre = {
            "name": self.name,
            "ext": self.ext,
            "files": self.file,
            "stagingDir": self.staging_dir,
            "tags": [self.name.replace("_", "-")] + add_tags
        }

        if range:
            repre.update({
                "frameStart": self.first_frame,
                "frameEnd": self.last_frame,
            })

        if self.multiple_presets:
            repre["outputName"] = self.name

        if self.publish_on_farm:
            repre["tags"].append("publish_on_farm")

        self.data["representations"].append(repre)

    def get_view_input_process_node(self):
        """
        Will get any active view process.

        Arguments:
            self (class): in object definition

        Returns:
            nuke.Node: copy node of Input Process node
        """
        reset_selection()
        ipn_orig = None
        for v in nuke.allNodes(filter="Viewer"):
            ip = v["input_process"].getValue()
            ipn = v["input_process_node"].getValue()
            if "VIEWER_INPUT" not in ipn and ip:
                ipn_orig = nuke.toNode(ipn)
                ipn_orig.setSelected(True)

        if ipn_orig:
            # copy selected to clipboard
            nuke.nodeCopy("%clipboard%")
            # reset selection
            reset_selection()
            # paste node and selection is on it only
            nuke.nodePaste("%clipboard%")
            # assign to variable
            ipn = nuke.selectedNode()

            return ipn

    def get_imageio_baking_profile(self):
        from . import lib as opnlib
        nuke_imageio = opnlib.get_nuke_imageio_settings()

        # TODO: this is only securing backward compatibility lets remove
        # this once all projects's anotomy are updated to newer config
        if "baking" in nuke_imageio.keys():
            return nuke_imageio["baking"]["viewerProcess"]
        else:
            return nuke_imageio["viewer"]["viewerProcess"]




class ExporterReviewLut(ExporterReview):
    """
    Generator object for review lut from Nuke

    Args:
        klass (pyblish.plugin): pyblish plugin parent
        instance (pyblish.instance): instance of pyblish context


    """
    _temp_nodes = []

    def __init__(self,
                 klass,
                 instance,
                 name=None,
                 ext=None,
                 cube_size=None,
                 lut_size=None,
                 lut_style=None,
                 multiple_presets=True):
        # initialize parent class
        super(ExporterReviewLut, self).__init__(
            klass, instance, multiple_presets)

        # deal with now lut defined in viewer lut
        if hasattr(klass, "viewer_lut_raw"):
            self.viewer_lut_raw = klass.viewer_lut_raw
        else:
            self.viewer_lut_raw = False

        self.name = name or "baked_lut"
        self.ext = ext or "cube"
        self.cube_size = cube_size or 32
        self.lut_size = lut_size or 1024
        self.lut_style = lut_style or "linear"

        # set frame start / end and file name to self
        self.get_file_info()

        self.log.info("File info was set...")

        self.file = self.fhead + self.name + ".{}".format(self.ext)
        self.path = os.path.join(
            self.staging_dir, self.file).replace("\\", "/")

    def clean_nodes(self):
        for node in self._temp_nodes:
            nuke.delete(node)
        self._temp_nodes = []
        self.log.info("Deleted nodes...")

    def generate_lut(self):
        bake_viewer_process = kwargs["bake_viewer_process"]
        bake_viewer_input_process_node = kwargs[
            "bake_viewer_input_process"]

        # ---------- start nodes creation

        # CMSTestPattern
        cms_node = nuke.createNode("CMSTestPattern")
        cms_node["cube_size"].setValue(self.cube_size)
        # connect
        self._temp_nodes.append(cms_node)
        self.previous_node = cms_node
        self.log.debug("CMSTestPattern...   `{}`".format(self._temp_nodes))

        if bake_viewer_process:
            # Node View Process
            if bake_viewer_input_process_node:
                ipn = self.get_view_input_process_node()
                if ipn is not None:
                    # connect
                    ipn.setInput(0, self.previous_node)
                    self._temp_nodes.append(ipn)
                    self.previous_node = ipn
                    self.log.debug(
                        "ViewProcess...   `{}`".format(self._temp_nodes))

            if not self.viewer_lut_raw:
                # OCIODisplay
                dag_node = nuke.createNode("OCIODisplay")
                # connect
                dag_node.setInput(0, self.previous_node)
                self._temp_nodes.append(dag_node)
                self.previous_node = dag_node
                self.log.debug("OCIODisplay...   `{}`".format(self._temp_nodes))

        # GenerateLUT
        gen_lut_node = nuke.createNode("GenerateLUT")
        gen_lut_node["file"].setValue(self.path)
        gen_lut_node["file_type"].setValue(".{}".format(self.ext))
        gen_lut_node["lut1d"].setValue(self.lut_size)
        gen_lut_node["style1d"].setValue(self.lut_style)
        # connect
        gen_lut_node.setInput(0, self.previous_node)
        self._temp_nodes.append(gen_lut_node)
        self.log.debug("GenerateLUT...   `{}`".format(self._temp_nodes))

        # ---------- end nodes creation

        # Export lut file
        nuke.execute(
            gen_lut_node.name(),
            int(self.first_frame),
            int(self.first_frame))

        self.log.info("Exported...")

        # ---------- generate representation data
        self.get_representation_data()

        self.log.debug("Representation...   `{}`".format(self.data))

        # ---------- Clean up
        self.clean_nodes()

        return self.data


class ExporterReviewMov(ExporterReview):
    """
    Metaclass for generating review mov files

    Args:
        klass (pyblish.plugin): pyblish plugin parent
        instance (pyblish.instance): instance of pyblish context

    """
    _temp_nodes = {}

    def __init__(self,
                 klass,
                 instance,
                 name=None,
                 ext=None,
                 multiple_presets=True
                 ):
        # initialize parent class
        super(ExporterReviewMov, self).__init__(
            klass, instance, multiple_presets)
        # passing presets for nodes to self
        self.nodes = klass.nodes if hasattr(klass, "nodes") else {}

        # deal with now lut defined in viewer lut
        self.viewer_lut_raw = klass.viewer_lut_raw
        self.write_colorspace = instance.data["colorspace"]

        self.name = name or "baked"
        self.ext = ext or "mov"

        # set frame start / end and file name to self
        self.get_file_info()

        self.log.info("File info was set...")

        self.file = self.fhead + self.name + ".{}".format(self.ext)
        self.path = os.path.join(
            self.staging_dir, self.file).replace("\\", "/")

    def clean_nodes(self, node_name):
        for node in self._temp_nodes[node_name]:
            nuke.delete(node)
        self._temp_nodes[node_name] = []
        self.log.info("Deleted nodes...")

    def render(self, render_node_name):
        self.log.info("Rendering...  ")
        # Render Write node
        nuke.execute(
            render_node_name,
            int(self.first_frame),
            int(self.last_frame))

        self.log.info("Rendered...")

    def save_file(self):
        import shutil
        with maintained_selection():
            self.log.info("Saving nodes as file...  ")
            # create nk path
            path = os.path.splitext(self.path)[0] + ".nk"
            # save file to the path
            shutil.copyfile(self.instance.context.data["currentFile"], path)

        self.log.info("Nodes exported...")
        return path

    def generate_mov(self, farm=False, **kwargs):
        self.publish_on_farm = farm
        read_raw = kwargs["read_raw"]
        reformat_node_add = kwargs["reformat_node_add"]
        reformat_node_config = kwargs["reformat_node_config"]
        bake_viewer_process = kwargs["bake_viewer_process"]
        bake_viewer_input_process_node = kwargs[
            "bake_viewer_input_process"]
        viewer_process_override = kwargs[
            "viewer_process_override"]

        baking_view_profile = (
            viewer_process_override or self.get_imageio_baking_profile())

        fps = self.instance.context.data["fps"]

        self.log.debug(">> baking_view_profile   `{}`".format(
            baking_view_profile))

        add_tags = kwargs.get("add_tags", [])

        self.log.info(
            "__ add_tags: `{0}`".format(add_tags))

        subset = self.instance.data["subset"]
        self._temp_nodes[subset] = []
        # ---------- start nodes creation

        # Read node
        r_node = nuke.createNode("Read")
        r_node["file"].setValue(self.path_in)
        r_node["first"].setValue(self.first_frame)
        r_node["origfirst"].setValue(self.first_frame)
        r_node["last"].setValue(self.last_frame)
        r_node["origlast"].setValue(self.last_frame)
        r_node["colorspace"].setValue(self.write_colorspace)

        if read_raw:
            r_node["raw"].setValue(1)

        # connect
        self._temp_nodes[subset].append(r_node)
        self.previous_node = r_node
        self.log.debug("Read...   `{}`".format(self._temp_nodes[subset]))

        # add reformat node
        if reformat_node_add:
            # append reformated tag
            add_tags.append("reformated")

            rf_node = nuke.createNode("Reformat")
            for kn_conf in reformat_node_config:
                _type = kn_conf["type"]
                k_name = str(kn_conf["name"])
                k_value = kn_conf["value"]

                # to remove unicode as nuke doesn't like it
                if _type == "string":
                    k_value = str(kn_conf["value"])

                rf_node[k_name].setValue(k_value)

            # connect
            rf_node.setInput(0, self.previous_node)
            self._temp_nodes[subset].append(rf_node)
            self.previous_node = rf_node
            self.log.debug(
                "Reformat...   `{}`".format(self._temp_nodes[subset]))

        # only create colorspace baking if toggled on
        if bake_viewer_process:
            if bake_viewer_input_process_node:
                # View Process node
                ipn = self.get_view_input_process_node()
                if ipn is not None:
                    # connect
                    ipn.setInput(0, self.previous_node)
                    self._temp_nodes[subset].append(ipn)
                    self.previous_node = ipn
                    self.log.debug(
                        "ViewProcess...   `{}`".format(
                            self._temp_nodes[subset]))

            if not self.viewer_lut_raw:
                # OCIODisplay
                dag_node = nuke.createNode("OCIODisplay")
                dag_node["view"].setValue(str(baking_view_profile))

                # connect
                dag_node.setInput(0, self.previous_node)
                self._temp_nodes[subset].append(dag_node)
                self.previous_node = dag_node
                self.log.debug("OCIODisplay...   `{}`".format(
                    self._temp_nodes[subset]))

        # Write node
        write_node = nuke.createNode("Write")
        self.log.debug("Path: {}".format(self.path))
        write_node["file"].setValue(str(self.path))
        write_node["file_type"].setValue(str(self.ext))

        # Knobs `meta_codec` and `mov64_codec` are not available on centos.
        # TODO shouldn't this come from settings on outputs?
        try:
            write_node["meta_codec"].setValue("ap4h")
        except Exception:
            self.log.info("`meta_codec` knob was not found")

        try:
            write_node["mov64_codec"].setValue("ap4h")
            write_node["mov64_fps"].setValue(float(fps))
        except Exception:
            self.log.info("`mov64_codec` knob was not found")

        write_node["mov64_write_timecode"].setValue(1)
        write_node["raw"].setValue(1)
        # connect
        write_node.setInput(0, self.previous_node)
        self._temp_nodes[subset].append(write_node)
        self.log.debug("Write...   `{}`".format(self._temp_nodes[subset]))
        # ---------- end nodes creation

        # ---------- render or save to nk
        if self.publish_on_farm:
            nuke.scriptSave()
            path_nk = self.save_file()
            self.data.update({
                "bakeScriptPath": path_nk,
                "bakeWriteNodeName": write_node.name(),
                "bakeRenderPath": self.path
            })
        else:
            self.render(write_node.name())

        # ---------- generate representation data
        self.get_representation_data(
            tags=["review", "delete"] + add_tags,
            range=True
        )

        self.log.debug("Representation...   `{}`".format(self.data))

        self.clean_nodes(subset)
        nuke.scriptSave()

        return self.data


class AbstractWriteRender(OpenPypeCreator):
    """Abstract creator to gather similar implementation for Write creators"""
    name = ""
    label = ""
    hosts = ["nuke"]
    n_class = "Write"
    family = "render"
    icon = "sign-out"
    defaults = ["Main", "Mask"]

    def __init__(self, *args, **kwargs):
        super(AbstractWriteRender, self).__init__(*args, **kwargs)

        data = OrderedDict()

        data["family"] = self.family
        data["families"] = self.n_class

        for k, v in self.data.items():
            if k not in data.keys():
                data.update({k: v})

        self.data = data
        self.nodes = nuke.selectedNodes()
        self.log.debug("_ self.data: '{}'".format(self.data))

    def process(self):

        inputs = []
        outputs = []
        instance = nuke.toNode(self.data["subset"])
        selected_node = None

        # use selection
        if (self.options or {}).get("useSelection"):
            nodes = self.nodes

            if not (len(nodes) < 2):
                msg = ("Select only one node. "
                       "The node you want to connect to, "
                       "or tick off `Use selection`")
                self.log.error(msg)
                nuke.message(msg)
                return

            if len(nodes) == 0:
                msg = (
                    "No nodes selected. Please select a single node to connect"
                    " to or tick off `Use selection`"
                )
                self.log.error(msg)
                nuke.message(msg)
                return

            selected_node = nodes[0]
            inputs = [selected_node]
            outputs = selected_node.dependent()

            if instance:
                if (instance.name() in selected_node.name()):
                    selected_node = instance.dependencies()[0]

        # if node already exist
        if instance:
            # collect input / outputs
            inputs = instance.dependencies()
            outputs = instance.dependent()
            selected_node = inputs[0]
            # remove old one
            nuke.delete(instance)

        # recreate new
        write_data = {
            "nodeclass": self.n_class,
            "families": [self.family],
            "avalon": self.data
        }

        # add creator data
        creator_data = {"creator": self.__class__.__name__}
        self.data.update(creator_data)
        write_data.update(creator_data)

        if self.presets.get('fpath_template'):
            self.log.info("Adding template path from preset")
            write_data.update(
                {"fpath_template": self.presets["fpath_template"]}
            )
        else:
            self.log.info("Adding template path from plugin")
            write_data.update({
                "fpath_template":
                    ("{work}/" + self.family + "s/nuke/{subset}"
                     "/{subset}.{frame}.{ext}")})

        write_node = self._create_write_node(selected_node,
                                             inputs, outputs,
                                             write_data)

        # relinking to collected connections
        for i, input in enumerate(inputs):
            write_node.setInput(i, input)

        write_node.autoplace()

        for output in outputs:
            output.setInput(0, write_node)

        write_node = self._modify_write_node(write_node)

        return write_node

    @abstractmethod
    def _create_write_node(self, selected_node, inputs, outputs, write_data):
        """Family dependent implementation of Write node creation

        Args:
            selected_node (nuke.Node)
            inputs (list of nuke.Node) - input dependencies (what is connected)
            outputs (list of nuke.Node) - output dependencies
            write_data (dict) - values used to fill Knobs
        Returns:
            node (nuke.Node): group node with  data as Knobs
        """
        pass

    @abstractmethod
    def _modify_write_node(self, write_node):
        """Family dependent modification of created 'write_node'

        Returns:
            node (nuke.Node): group node with data as Knobs
        """
        pass
