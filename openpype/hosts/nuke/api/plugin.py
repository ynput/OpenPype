import nuke
import re
import os
import sys
import six
import random
import string
from collections import OrderedDict, defaultdict
from abc import abstractmethod

from openpype.settings import get_current_project_settings
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
    get_current_task_name
)
from openpype.pipeline.colorspace import (
    get_display_view_colorspace_name,
    get_colorspace_settings_from_publish_context,
    set_colorspace_data_to_representation
)
from openpype.lib.transcoding import (
    VIDEO_EXTENSIONS
)
from .lib import (
    INSTANCE_DATA_KNOB,
    Knobby,
    check_subsetname_exists,
    maintained_selection,
    get_avalon_knob_data,
    set_avalon_knob_data,
    add_publish_knob,
    get_nuke_imageio_settings,
    set_node_knobs_from_settings,
    set_node_data,
    get_node_data,
    get_view_process_node,
    get_viewer_config_from_string,
    deprecated,
    get_filenames_without_hash,
    link_knobs
)
from .pipeline import (
    list_instances,
    remove_instance
)


def _collect_and_cache_nodes(creator):
    key = "openpype.nuke.nodes"
    if key not in creator.collection_shared_data:
        instances_by_identifier = defaultdict(list)
        for item in list_instances():
            _, instance_data = item
            identifier = instance_data["creator_identifier"]
            instances_by_identifier[identifier].append(item)
        creator.collection_shared_data[key] = instances_by_identifier
    return creator.collection_shared_data[key]


class NukeCreatorError(CreatorError):
    pass


class NukeCreator(NewCreator):
    selected_nodes = []

    def pass_pre_attributes_to_instance(
        self,
        instance_data,
        pre_create_data,
        keys=None
    ):
        if not keys:
            keys = pre_create_data.keys()

        creator_attrs = instance_data["creator_attributes"] = {}
        for pass_key in keys:
            creator_attrs[pass_key] = pre_create_data[pass_key]

    def check_existing_subset(self, subset_name):
        """Make sure subset name is unique.

        It search within all nodes recursively
        and checks if subset name is found in
        any node having instance data knob.

        Arguments:
            subset_name (str): Subset name
        """

        for node in nuke.allNodes(recurseGroups=True):
            # make sure testing node is having instance knob
            if INSTANCE_DATA_KNOB not in node.knobs().keys():
                continue
            node_data = get_node_data(node, INSTANCE_DATA_KNOB)

            if not node_data:
                # a node has no instance data
                continue

            # test if subset name is matching
            if node_data.get("subset") == subset_name:
                raise NukeCreatorError(
                    (
                        "A publish instance for '{}' already exists "
                        "in nodes! Please change the variant "
                        "name to ensure unique output."
                    ).format(subset_name)
                )

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

    def create(self, subset_name, instance_data, pre_create_data):

        # make sure selected nodes are added
        self.set_selected_nodes(pre_create_data)

        # make sure subset name is unique
        self.check_existing_subset(subset_name)

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
        cached_instances = _collect_and_cache_nodes(self)
        attr_def_keys = {
            attr_def.key
            for attr_def in self.get_instance_attr_defs()
        }
        attr_def_keys.discard(None)

        for (node, data) in cached_instances[self.identifier]:
            created_instance = CreatedInstance.from_existing(
                data, self
            )
            created_instance.transient_data["node"] = node
            self._add_instance_to_context(created_instance)

            for key in (
                set(created_instance["creator_attributes"].keys())
                - attr_def_keys
            ):
                created_instance["creator_attributes"].pop(key)

    def update_instances(self, update_list):
        for created_inst, changes in update_list:
            instance_node = created_inst.transient_data["node"]

            # update instance node name if subset name changed
            if "subset" in changes.changed_keys:
                instance_node["name"].setValue(
                    changes["subset"].new_value
                )

            # in case node is not existing anymore (user erased it manually)
            try:
                instance_node.fullName()
            except ValueError:
                self.remove_instances([created_inst])
                continue

            set_node_data(
                instance_node,
                INSTANCE_DATA_KNOB,
                created_inst.data_to_store()
            )

    def remove_instances(self, instances):
        for instance in instances:
            remove_instance(instance)
            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        return [
            BoolDef(
                "use_selection",
                default=not self.create_context.headless,
                label="Use selection"
            )
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

    def get_linked_knobs(self):
        linked_knobs = []
        if "channels" in self.instance_attributes:
            linked_knobs.append("channels")
        if "ordered" in self.instance_attributes:
            linked_knobs.append("render_order")
        if "use_range_limit" in self.instance_attributes:
            linked_knobs.extend(["___", "first", "last", "use_limit"])

        return linked_knobs

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
        ]
        # add reviewable attribute
        if "reviewable" in self.instance_attributes:
            attr_defs.append(self._get_reviewable_bool())

        return attr_defs

    def _get_render_target_enum(self):
        rendering_targets = {
            "local": "Local machine rendering",
            "frames": "Use existing frames"
        }
        if ("farm_rendering" in self.instance_attributes):
            rendering_targets["frames_farm"] = "Use existing frames - farm"
            rendering_targets["farm"] = "Farm rendering"

        return EnumDef(
            "render_target",
            items=rendering_targets,
            label="Render target"
        )

    def _get_reviewable_bool(self):
        return BoolDef(
            "review",
            default=True,
            label="Review"
        )

    def create(self, subset_name, instance_data, pre_create_data):
        # make sure selected nodes are added
        self.set_selected_nodes(pre_create_data)

        # make sure subset name is unique
        self.check_existing_subset(subset_name)

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

    def apply_settings(self, project_settings):
        """Method called on initialization of plugin to apply settings."""

        # plugin settings
        plugin_settings = self.get_creator_settings(project_settings)

        # individual attributes
        self.instance_attributes = plugin_settings.get(
            "instance_attributes") or self.instance_attributes
        self.prenodes = plugin_settings["prenodes"]
        self.default_variants = plugin_settings.get(
            "default_variants") or self.default_variants
        self.temp_rendering_path_template = (
            plugin_settings.get("temp_rendering_path_template")
            or self.temp_rendering_path_template
        )


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


def get_instance_group_node_childs(instance):
    """Return list of instance group node children

    Args:
        instance (pyblish.Instance): pyblish instance

    Returns:
        list: [nuke.Node]
    """
    node = instance.data["transientData"]["node"]

    if node.Class() != "Group":
        return

    # collect child nodes
    child_nodes = []
    # iterate all nodes
    for node in nuke.allNodes(group=node):
        # add contained nodes to instance's node list
        child_nodes.append(node)

    return child_nodes


def get_colorspace_from_node(node):
    # Add version data to instance
    colorspace = node["colorspace"].value()

    # remove default part of the string
    if "default (" in colorspace:
        colorspace = re.sub(r"default.\(|\)", "", colorspace)

    return colorspace


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
        parent_class = parent_node.Class()
        members = self.get_members(parent_node)

        dependent_nodes = None
        for node in members:
            _depndc = [n for n in node.dependent() if n not in members]
            if not _depndc:
                continue

            dependent_nodes = _depndc
            break

        for member in members:
            if member.Class() == parent_class:
                continue
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
        self.data = {"representations": []}

    def get_file_info(self):
        if self.collection:
            # get path
            self.fname = os.path.basename(
                self.collection.format("{head}{padding}{tail}")
            )
            self.fhead = self.collection.format("{head}")

            # get first and last frame
            self.first_frame = min(self.collection.indexes)
            self.last_frame = max(self.collection.indexes)

            # make sure slate frame is not included
            frame_start_handle = self.instance.data["frameStartHandle"]
            if frame_start_handle > self.first_frame:
                self.first_frame = frame_start_handle

        else:
            self.fname = os.path.basename(self.path_in)
            self.fhead = os.path.splitext(self.fname)[0] + "."
            self.first_frame = self.instance.data["frameStartHandle"]
            self.last_frame = self.instance.data["frameEndHandle"]

        if "#" in self.fhead:
            self.fhead = self.fhead.replace("#", "")[:-1]

    def get_representation_data(
        self, tags=None, range=False,
        custom_tags=None, colorspace=None
    ):
        """ Add representation data to self.data

        Args:
            tags (list[str], optional): list of defined tags.
                                        Defaults to None.
            range (bool, optional): flag for adding ranges.
                                    Defaults to False.
            custom_tags (list[str], optional): user inputted custom tags.
                                               Defaults to None.
        """
        add_tags = tags or []
        repre = {
            "name": self.name,
            "ext": self.ext,
            "files": self.file,
            "stagingDir": self.staging_dir,
            "tags": [self.name.replace("_", "-")] + add_tags
        }

        if custom_tags:
            repre["custom_tags"] = custom_tags

        if range:
            repre.update({
                "frameStart": self.first_frame,
                "frameEnd": self.last_frame,
            })
        if ".{}".format(self.ext) not in VIDEO_EXTENSIONS:
            filenames = get_filenames_without_hash(
                self.file, self.first_frame, self.last_frame)
            repre["files"] = filenames

        if self.multiple_presets:
            repre["outputName"] = self.name

        if self.publish_on_farm:
            repre["tags"].append("publish_on_farm")

        # add colorspace data to representation
        if colorspace:
            set_colorspace_data_to_representation(
                repre,
                self.instance.context.data,
                colorspace=colorspace,
                log=self.log
            )
        self.data["representations"].append(repre)

    def get_imageio_baking_profile(self):
        from . import lib as opnlib
        nuke_imageio = opnlib.get_nuke_imageio_settings()

        # TODO: this is only securing backward compatibility lets remove
        # this once all projects's anatomy are updated to newer config
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
                self.log.debug(
                    "OCIODisplay...   `{}`".format(self._temp_nodes))

        # GenerateLUT
        gen_lut_node = nuke.createNode("GenerateLUT")
        gen_lut_node["file"].setValue(self.path)
        gen_lut_node["file_type"].setValue(".{}".format(self.ext))
        gen_lut_node["lut1d"].setValue(self.lut_size)
        gen_lut_node["style1d"].setValue(self.lut_style)
        # connect
        gen_lut_node.setInput(0, self.previous_node)
        self._temp_nodes.append(gen_lut_node)
        # ---------- end nodes creation

        # Export lut file
        nuke.execute(
            gen_lut_node.name(),
            int(self.first_frame),
            int(self.first_frame))

        self.log.info("Exported...")

        # ---------- generate representation data
        self.get_representation_data()

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

        if ".{}".format(self.ext) in VIDEO_EXTENSIONS:
            self.file = "{}{}.{}".format(
                self.fhead, self.name, self.ext)
        else:
            # Output is image (or image sequence)
            # When the file is an image it's possible it
            # has extra information after the `fhead` that
            # we want to preserve, e.g. like frame numbers
            # or frames hashes like `####`
            filename_no_ext = os.path.splitext(
                os.path.basename(self.path_in))[0]
            after_head = filename_no_ext[len(self.fhead):]
            self.file = "{}{}.{}.{}".format(
                self.fhead, self.name, after_head, self.ext)
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
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            shutil.copyfile(self.instance.context.data["currentFile"], path)

        self.log.info("Nodes exported...")
        return path

    def generate_mov(self, farm=False, **kwargs):
        # colorspace data
        colorspace = None
        # get colorspace settings
        # get colorspace data from context
        config_data, _ = get_colorspace_settings_from_publish_context(
            self.instance.context.data)

        add_tags = []
        self.publish_on_farm = farm
        read_raw = kwargs["read_raw"]
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

        add_custom_tags = kwargs.get("add_custom_tags", [])

        self.log.info(
            "__ add_custom_tags: `{0}`".format(add_custom_tags))

        subset = self.instance.data["subset"]
        self._temp_nodes[subset] = []

        # Read node
        r_node = nuke.createNode("Read")
        r_node["file"].setValue(self.path_in)
        r_node["first"].setValue(self.first_frame)
        r_node["origfirst"].setValue(self.first_frame)
        r_node["last"].setValue(self.last_frame)
        r_node["origlast"].setValue(self.last_frame)
        r_node["colorspace"].setValue(self.write_colorspace)

        # do not rely on defaults, set explicitly
        # to be sure it is set correctly
        r_node["frame_mode"].setValue("expression")
        r_node["frame"].setValue("")

        if read_raw:
            r_node["raw"].setValue(1)

        # connect to Read node
        self._shift_to_previous_node_and_temp(subset, r_node, "Read...   `{}`")

        # add reformat node
        reformat_nodes_config = kwargs["reformat_nodes_config"]
        if reformat_nodes_config["enabled"]:
            reposition_nodes = reformat_nodes_config["reposition_nodes"]
            for reposition_node in reposition_nodes:
                node_class = reposition_node["node_class"]
                knobs = reposition_node["knobs"]
                node = nuke.createNode(node_class)
                set_node_knobs_from_settings(node, knobs)

                # connect in order
                self._connect_to_above_nodes(
                    node, subset, "Reposition node...   `{}`"
                )
            # append reformated tag
            add_tags.append("reformated")

        # only create colorspace baking if toggled on
        if bake_viewer_process:
            if bake_viewer_input_process_node:
                # View Process node
                ipn = get_view_process_node()
                if ipn is not None:
                    # connect to ViewProcess node
                    self._connect_to_above_nodes(ipn, subset, "ViewProcess...   `{}`")

            if not self.viewer_lut_raw:
                # OCIODisplay
                dag_node = nuke.createNode("OCIODisplay")

                # assign display
                display, viewer = get_viewer_config_from_string(
                    str(baking_view_profile)
                )
                if display:
                    dag_node["display"].setValue(display)

                # assign viewer
                dag_node["view"].setValue(viewer)

                if config_data:
                    # convert display and view to colorspace
                    colorspace = get_display_view_colorspace_name(
                        config_path=config_data["path"],
                        display=display,
                        view=viewer
                    )

                self._connect_to_above_nodes(dag_node, subset, "OCIODisplay...   `{}`")
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

        try:
            write_node["mov64_write_timecode"].setValue(1)
        except Exception:
            self.log.info("`mov64_write_timecode` knob was not found")

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
            tags=["review", "need_thumbnail", "delete"] + add_tags,
            custom_tags=add_custom_tags,
            range=True,
            colorspace=colorspace
        )

        self.log.debug("Representation...   `{}`".format(self.data))

        self.clean_nodes(subset)
        nuke.scriptSave()

        return self.data

    def _shift_to_previous_node_and_temp(self, subset, node, message):
        self._temp_nodes[subset].append(node)
        self.previous_node = node
        self.log.debug(message.format(self._temp_nodes[subset]))

    def _connect_to_above_nodes(self, node, subset, message):
        node.setInput(0, self.previous_node)
        self._shift_to_previous_node_and_temp(subset, node, message)


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

        In case where `type` key is missing in single
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


def convert_to_valid_instaces():
    """ Check and convert to latest publisher instances

    Also save as new minor version of workfile.
    """
    def family_to_identifier(family):
        mapping = {
            "render": "create_write_render",
            "prerender": "create_write_prerender",
            "still": "create_write_image",
            "model": "create_model",
            "camera": "create_camera",
            "nukenodes": "create_backdrop",
            "gizmo": "create_gizmo",
            "source": "create_source"

        }
        return mapping[family]

    from openpype.hosts.nuke.api import workio

    task_name = get_current_task_name()

    # save into new workfile
    current_file = workio.current_file()

    # add file suffex if not
    if "_publisherConvert" not in current_file:
        new_workfile = (
            current_file[:-3]
            + "_publisherConvert"
            + current_file[-3:]
        )
    else:
        new_workfile = current_file

    path = new_workfile.replace("\\", "/")
    nuke.scriptSaveAs(new_workfile, overwrite=1)
    nuke.Root()["name"].setValue(path)
    nuke.Root()["project_directory"].setValue(os.path.dirname(path))
    nuke.Root().setModified(False)

    _remove_old_knobs(nuke.Root())

    # loop all nodes and convert
    for node in nuke.allNodes(recurseGroups=True):
        transfer_data = {
            "creator_attributes": {}
        }
        creator_attr = transfer_data["creator_attributes"]

        if node.Class() in ["Viewer", "Dot"]:
            continue

        if get_node_data(node, INSTANCE_DATA_KNOB):
            continue

        # get data from avalon knob
        avalon_knob_data = get_avalon_knob_data(
            node, ["avalon:", "ak:"])

        if not avalon_knob_data:
            continue

        if avalon_knob_data["id"] != "pyblish.avalon.instance":
            continue

        transfer_data.update({
            k: v for k, v in avalon_knob_data.items()
            if k not in ["families", "creator"]
        })

        transfer_data["task"] = task_name

        family = avalon_knob_data["family"]
        # establish families
        families_ak = avalon_knob_data.get("families", [])

        if "suspend_publish" in node.knobs():
            creator_attr["suspended_publish"] = (
                node["suspend_publish"].value())

        # get review knob value
        if "review" in node.knobs():
            creator_attr["review"] = (
                node["review"].value())

        if "publish" in node.knobs():
            transfer_data["active"] = (
                node["publish"].value())

        # add idetifier
        transfer_data["creator_identifier"] = family_to_identifier(family)

        # Add all nodes in group instances.
        if node.Class() == "Group":
            # only alter families for render family
            if families_ak and "write" in families_ak.lower():
                target = node["render"].value()
                if target == "Use existing frames":
                    creator_attr["render_target"] = "frames"
                elif target == "Local":
                    # Local rendering
                    creator_attr["render_target"] = "local"
                elif target == "On farm":
                    # Farm rendering
                    creator_attr["render_target"] = "farm"

                if "deadlinePriority" in node.knobs():
                    transfer_data["farm_priority"] = (
                        node["deadlinePriority"].value())
                if "deadlineChunkSize" in node.knobs():
                    creator_attr["farm_chunk"] = (
                        node["deadlineChunkSize"].value())
                if "deadlineConcurrentTasks" in node.knobs():
                    creator_attr["farm_concurrency"] = (
                        node["deadlineConcurrentTasks"].value())

        _remove_old_knobs(node)

        # add new instance knob with transfer data
        set_node_data(
            node, INSTANCE_DATA_KNOB, transfer_data)

    nuke.scriptSave()


def _remove_old_knobs(node):
    remove_knobs = [
        "review", "publish", "render", "suspend_publish", "warn", "divd",
        "OpenpypeDataGroup", "OpenpypeDataGroup_End", "deadlinePriority",
        "deadlineChunkSize", "deadlineConcurrentTasks", "Deadline"
    ]
    print(node.name())

    # remove all old knobs
    for knob in node.allKnobs():
        try:
            if knob.name() in remove_knobs:
                node.removeKnob(knob)
            elif "avalon" in knob.name():
                node.removeKnob(knob)
        except ValueError:
            pass


def exposed_write_knobs(settings, plugin_name, instance_node):
    exposed_knobs = settings["nuke"]["create"][plugin_name].get(
        "exposed_knobs", []
    )
    if exposed_knobs:
        instance_node.addKnob(nuke.Text_Knob('', 'Write Knobs'))
    write_node = nuke.allNodes(group=instance_node, filter="Write")[0]
    link_knobs(exposed_knobs, write_node, instance_node)
