from pprint import pformat
import nuke

import os
import sys
import six
import random
import string
from collections import OrderedDict
from abc import abstractmethod

from openpype.client import (
    get_asset_by_name,
    get_subsets,
)

from openpype.api import get_current_project_settings
from openpype.lib import (
    BoolDef,
    EnumDef
)
from openpype.pipeline import (
    LegacyCreator,
    LoaderPlugin,
    CreatorError,
    Creator as NewCreator,
    CreatedInstance,
    legacy_io
)
from .lib import (
    INSTANCE_DATA_KNOB,
    Knobby,
    check_subsetname_exists,
    maintained_selection,
    set_avalon_knob_data,
    add_publish_knob,
    get_nuke_imageio_settings,
    set_node_knobs_from_settings,
    get_view_process_node,
    set_node_data,
    deprecated
)
from .pipeline import (
    list_instances,
    remove_instance
)


class NukeCreatorError(CreatorError):
    pass


class NukeCreator(NewCreator):
    selected_nodes = []

    def add_info_knob(self, node):
        if "OP_info" in node.knobs().keys():
            return

        # add info text
        info_knob = nuke.Text_Knob("OP_info", "")
        info_knob.setValue("""
<span style=\"color:#fc0303\">
<p>This node is maintained by <b>OpenPype Publisher</b>.</p>
<p>To remove it use Publisher gui.</p>
</span>
        """)
        node.addKnob(info_knob)

    def check_existing_subset(self, subset_name, instance_data):
        """Check if existing subset name versions already exists."""
        # Get all subsets of the current asset
        project_name = legacy_io.active_project()
        asset_doc = get_asset_by_name(
            project_name, instance_data["asset"], fields=["_id"]
        )
        subset_docs = get_subsets(
            project_name, asset_ids=[asset_doc["_id"]], fields=["name"]
        )
        existing_subset_names_low = {
            subset_doc["name"].lower()
            for subset_doc in subset_docs
        }
        return subset_name.lower() in existing_subset_names_low

    def create_instance_node(
        self,
        node_name,
        knobs=None,
        parent=None,
        node_type=None
    ):
        """Create node representing instance.

        Arguments:
            node_name (str): Name of the new node.
            knobs (OrderedDict): node knobs name and values
            parent (str): Name of the parent node.
            node_type (str, optional): Nuke node Class.

        Returns:
            nuke.Node: Newly created instance node.

        """
        node_type = node_type or "NoOp"

        node_knobs = knobs or {}

        # set parent node
        parent_node = nuke.root()
        if parent:
            parent_node = nuke.toNode(parent)

        try:
            with parent_node:
                created_node = nuke.createNode(node_type)
                created_node["name"].setValue(node_name)

                self.add_info_knob(created_node)

                for key, values in node_knobs.items():
                    if key in created_node.knobs():
                        created_node["key"].setValue(values)
        except Exception as _err:
            raise NukeCreatorError("Creating have failed: {}".format(_err))

        return created_node

    def set_selected_nodes(self, pre_create_data):
        if pre_create_data.get("use_selection"):
            self.selected_nodes = nuke.selectedNodes()
            if self.selected_nodes == []:
                raise NukeCreatorError("Creator error: No active selection")
        else:
            self.selected_nodes = []

        self.log.debug("Selection is: {}".format(self.selected_nodes))

    def create(self, subset_name, instance_data, pre_create_data):

        # make sure selected nodes are added
        self.set_selected_nodes(pre_create_data)

        # make sure subset name is unique
        if self.check_existing_subset(subset_name, instance_data):
            raise NukeCreatorError(
                ("subset {} is already published"
                 "definition.").format(subset_name))

        try:

            instance_node = self.create_instance_node(
                subset_name,
                node_type=instance_data.pop("node_type", None)
            )
            instance = CreatedInstance(
                self.family,
                subset_name,
                instance_data,
                self
            )

            instance.transient_data["node"] = instance_node

            self._add_instance_to_context(instance)

            set_node_data(
                instance_node, INSTANCE_DATA_KNOB, instance.data_to_store())

            return instance

        except Exception as er:
            six.reraise(
                NukeCreatorError,
                NukeCreatorError("Creator error: {}".format(er)),
                sys.exc_info()[2])

    def collect_instances(self):
        for (node, data) in list_instances(creator_id=self.identifier):
            created_instance = CreatedInstance.from_existing(
                data, self
            )
            created_instance.transient_data["node"] = node
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            instance_node = created_inst.transient_data["node"]
            current_data = created_inst.data

            set_node_data(
                instance_node,
                INSTANCE_DATA_KNOB,
                {
                    key: value[1] for key, value in _changes.items()
                    if current_data.get(key) != value[0]
                }
            )

    def remove_instances(self, instances):
        for instance in instances:
            remove_instance(instance)
            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection", label="Use selection")
        ]

    def get_creator_settings(self, project_settings, settings_key=None):
        if not settings_key:
            settings_key = self.__class__.__name__
        return project_settings["nuke"]["create"][settings_key]


class NukeWriteCreator(NukeCreator):
    """Add Publishable Write node"""

    identifier = "create_write"
    label = "Create Write"
    family = "write"
    icon = "sign-out"

    def integrate_links(self, node, outputs=True):
        # skip if no selection
        if not self.selected_node:
            return

        # collect dependencies
        input_nodes = [self.selected_node]
        dependent_nodes = self.selected_node.dependent() if outputs else []

        # relinking to collected connections
        for i, input in enumerate(input_nodes):
            node.setInput(i, input)

        # make it nicer in graph
        node.autoplace()

        # relink also dependent nodes
        for dep_nodes in dependent_nodes:
            dep_nodes.setInput(0, node)

    def set_selected_nodes(self, pre_create_data):
        if pre_create_data.get("use_selection"):
            selected_nodes = nuke.selectedNodes()
            if selected_nodes == []:
                raise NukeCreatorError("Creator error: No active selection")
            elif len(selected_nodes) > 1:
                NukeCreatorError("Creator error: Select only one camera node")
            self.selected_node = selected_nodes[0]
        else:
            self.selected_node = None

    def get_pre_create_attr_defs(self):
        attr_defs = [
            BoolDef("use_selection", label="Use selection"),
            self._get_render_target_enum()
        ]
        return attr_defs

    def get_instance_attr_defs(self):
        attr_defs = [
            self._get_render_target_enum(),
            self._get_reviewable_bool()
        ]
        return attr_defs

    def _get_render_target_enum(self):
        rendering_targets = {
            "local": "Local machine rendering",
            "frames": "Use existing frames"
        }
        if ("farm_rendering" in self.instance_attributes):
            rendering_targets["farm"] = "Farm rendering"

        return EnumDef(
            "render_target",
            items=rendering_targets,
            label="Render target"
        )

    def _get_reviewable_bool(self):
        return BoolDef(
            "review",
            default=("reviewable" in self.instance_attributes),
            label="Review"
        )

    def create(self, subset_name, instance_data, pre_create_data):
        # make sure selected nodes are added
        self.set_selected_nodes(pre_create_data)

        # make sure subset name is unique
        if self.check_existing_subset(subset_name, instance_data):
            raise NukeCreatorError(
                ("subset {} is already published"
                 "definition.").format(subset_name))

        instance_node = self.create_instance_node(
            subset_name,
            instance_data
        )

        try:
            instance = CreatedInstance(
                self.family,
                subset_name,
                instance_data,
                self
            )

            instance.transient_data["node"] = instance_node

            self._add_instance_to_context(instance)

            set_node_data(
                instance_node, INSTANCE_DATA_KNOB, instance.data_to_store())

            return instance

        except Exception as er:
            six.reraise(
                NukeCreatorError,
                NukeCreatorError("Creator error: {}".format(er)),
                sys.exc_info()[2]
            )

    def apply_settings(
        self,
        project_settings,
        system_settings,
        # anatomy_settings
    ):
        """Method called on initialization of plugin to apply settings."""

        # plugin settings
        plugin_settings = self.get_creator_settings(project_settings)

        # individual attributes
        self.instance_attributes = plugin_settings[
            "instance_attributes"]
        self.prenodes = plugin_settings["prenodes"]
        self.default_variants = plugin_settings["default_variants"]
        self.temp_rendering_path_template = plugin_settings[
            "temp_rendering_path_template"]


class OpenPypeCreator(LegacyCreator):
    """Pype Nuke Creator class wrapper"""
    node_color = "0xdfea5dff"

    def __init__(self, *args, **kwargs):
        super(OpenPypeCreator, self).__init__(*args, **kwargs)
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

    def generate_lut(self, **kwargs):
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
                ipn = get_view_process_node()
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
            set_node_knobs_from_settings(rf_node, reformat_node_config)

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
                ipn = get_view_process_node()
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


@deprecated("openpype.hosts.nuke.api.plugin.NukeWriteCreator")
class AbstractWriteRender(OpenPypeCreator):
    """Abstract creator to gather similar implementation for Write creators"""
    name = ""
    label = ""
    hosts = ["nuke"]
    n_class = "Write"
    family = "render"
    icon = "sign-out"
    defaults = ["Main", "Mask"]
    knobs = []
    prenodes = {}

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
            "avalon": self.data,
            "subset": self.data["subset"],
            "knobs": self.knobs
        }

        # add creator data
        creator_data = {"creator": self.__class__.__name__}
        self.data.update(creator_data)
        write_data.update(creator_data)

        write_node = self._create_write_node(
            selected_node,
            inputs,
            outputs,
            write_data
        )

        # relinking to collected connections
        for i, input in enumerate(inputs):
            write_node.setInput(i, input)

        write_node.autoplace()

        for output in outputs:
            output.setInput(0, write_node)

        write_node = self._modify_write_node(write_node)

        return write_node

    def is_legacy(self):
        """Check if it needs to run legacy code

        In case where `type` key is missing in singe
        knob it is legacy project anatomy.

        Returns:
            bool: True if legacy
        """
        imageio_nodes = get_nuke_imageio_settings()["nodes"]
        node = imageio_nodes["requiredNodes"][0]
        if "type" not in node["knobs"][0]:
            # if type is not yet in project anatomy
            return True
        elif next(iter(
            _k for _k in node["knobs"]
            if _k.get("type") == "__legacy__"
        ), None):
            # in case someone re-saved anatomy
            # with old configuration
            return True

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
