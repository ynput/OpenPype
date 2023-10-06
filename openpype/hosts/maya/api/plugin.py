import json
import os
from abc import ABCMeta

import qargparse
import six
from maya import cmds
from maya.app.renderSetup.model import renderSetup

from openpype.lib import BoolDef, Logger
from openpype.settings import get_project_settings
from openpype.pipeline import (
    AVALON_CONTAINER_ID,
    Anatomy,

    CreatedInstance,
    Creator as NewCreator,
    AutoCreator,
    HiddenCreator,

    CreatorError,
    LegacyCreator,
    LoaderPlugin,
    get_representation_path,
)
from openpype.pipeline.load import LoadError
from openpype.client import get_asset_by_name
from openpype.pipeline.create import get_subset_name

from . import lib
from .lib import imprint, read
from .pipeline import containerise

log = Logger.get_logger()


def _get_attr(node, attr, default=None):
    """Helper to get attribute which allows attribute to not exist."""
    if not cmds.attributeQuery(attr, node=node, exists=True):
        return default
    return cmds.getAttr("{}.{}".format(node, attr))


# Backwards compatibility: these functions has been moved to lib.
def get_reference_node(*args, **kwargs):
    """Get the reference node from the container members

    Deprecated:
        This function was moved and will be removed in 3.16.x.
    """
    msg = "Function 'get_reference_node' has been moved."
    log.warning(msg)
    cmds.warning(msg)
    return lib.get_reference_node(*args, **kwargs)


def get_reference_node_parents(*args, **kwargs):
    """
    Deprecated:
        This function was moved and will be removed in 3.16.x.
    """
    msg = "Function 'get_reference_node_parents' has been moved."
    log.warning(msg)
    cmds.warning(msg)
    return lib.get_reference_node_parents(*args, **kwargs)


class Creator(LegacyCreator):
    defaults = ['Main']

    def process(self):
        nodes = list()

        with lib.undo_chunk():
            if (self.options or {}).get("useSelection"):
                nodes = cmds.ls(selection=True)

            instance = cmds.sets(nodes, name=self.name)
            lib.imprint(instance, self.data)

        return instance


@six.add_metaclass(ABCMeta)
class MayaCreatorBase(object):

    @staticmethod
    def cache_subsets(shared_data):
        """Cache instances for Creators to shared data.

        Create `maya_cached_subsets` key when needed in shared data and
        fill it with all collected instances from the scene under its
        respective creator identifiers.

        If legacy instances are detected in the scene, create
        `maya_cached_legacy_subsets` there and fill it with
        all legacy subsets under family as a key.

        Args:
            Dict[str, Any]: Shared data.

        Return:
            Dict[str, Any]: Shared data dictionary.

        """
        if shared_data.get("maya_cached_subsets") is None:
            cache = dict()
            cache_legacy = dict()

            for node in cmds.ls(type="objectSet"):

                if _get_attr(node, attr="id") != "pyblish.avalon.instance":
                    continue

                creator_id = _get_attr(node, attr="creator_identifier")
                if creator_id is not None:
                    # creator instance
                    cache.setdefault(creator_id, []).append(node)
                else:
                    # legacy instance
                    family = _get_attr(node, attr="family")
                    if family is None:
                        # must be a broken instance
                        continue

                    cache_legacy.setdefault(family, []).append(node)

            shared_data["maya_cached_subsets"] = cache
            shared_data["maya_cached_legacy_subsets"] = cache_legacy
        return shared_data

    def get_publish_families(self):
        """Return families for the instances of this creator.

        Allow a Creator to define multiple families so that a creator can
        e.g. specify `usd` and `usdMaya` and another USD creator can also
        specify `usd` but apply different extractors like `usdMultiverse`.

        There is no need to override this method if you only have the
        primary family defined by the `family` property as that will always
        be set.

        Returns:
            list: families for instances of this creator

        """
        return []

    def imprint_instance_node(self, node, data):

        # We never store the instance_node as value on the node since
        # it's the node name itself
        data.pop("instance_node", None)
        data.pop("instance_id", None)

        # Don't store `families` since it's up to the creator itself
        # to define the initial publish families - not a stored attribute of
        # `families`
        data.pop("families", None)

        # We store creator attributes at the root level and assume they
        # will not clash in names with `subset`, `task`, etc. and other
        # default names. This is just so these attributes in many cases
        # are still editable in the maya UI by artists.
        # note: pop to move to end of dict to sort attributes last on the node
        creator_attributes = data.pop("creator_attributes", {})

        # We only flatten value types which `imprint` function supports
        json_creator_attributes = {}
        for key, value in dict(creator_attributes).items():
            if isinstance(value, (list, tuple, dict)):
                creator_attributes.pop(key)
                json_creator_attributes[key] = value

        # Flatten remaining creator attributes to the node itself
        data.update(creator_attributes)

        # We know the "publish_attributes" will be complex data of
        # settings per plugins, we'll store this as a flattened json structure
        # pop to move to end of dict to sort attributes last on the node
        data["publish_attributes"] = json.dumps(
            data.pop("publish_attributes", {})
        )

        # Persist the non-flattened creator attributes (special value types,
        # like multiselection EnumDef)
        data["creator_attributes"] = json.dumps(json_creator_attributes)

        # Since we flattened the data structure for creator attributes we want
        # to correctly detect which flattened attributes should end back in the
        # creator attributes when reading the data from the node, so we store
        # the relevant keys as a string
        data["__creator_attributes_keys"] = ",".join(creator_attributes.keys())

        # Kill any existing attributes just so we can imprint cleanly again
        for attr in data.keys():
            if cmds.attributeQuery(attr, node=node, exists=True):
                cmds.deleteAttr("{}.{}".format(node, attr))

        return imprint(node, data)

    def read_instance_node(self, node):
        node_data = read(node)

        # Never care about a cbId attribute on the object set
        # being read as 'data'
        node_data.pop("cbId", None)

        # Make sure we convert any creator attributes from the json string
        creator_attributes = node_data.get("creator_attributes")
        if creator_attributes:
            node_data["creator_attributes"] = json.loads(creator_attributes)
        else:
            node_data["creator_attributes"] = {}

        # Move the relevant attributes into "creator_attributes" that
        # we flattened originally
        creator_attribute_keys = node_data.pop("__creator_attributes_keys",
                                               "").split(",")
        for key in creator_attribute_keys:
            if key in node_data:
                node_data["creator_attributes"][key] = node_data.pop(key)

        # Make sure we convert any publish attributes from the json string
        publish_attributes = node_data.get("publish_attributes")
        if publish_attributes:
            node_data["publish_attributes"] = json.loads(publish_attributes)

        # Explicitly re-parse the node name
        node_data["instance_node"] = node
        node_data["instance_id"] = node

        # If the creator plug-in specifies
        families = self.get_publish_families()
        if families:
            node_data["families"] = families

        return node_data

    def _default_collect_instances(self):
        self.cache_subsets(self.collection_shared_data)
        cached_subsets = self.collection_shared_data["maya_cached_subsets"]
        for node in cached_subsets.get(self.identifier, []):
            node_data = self.read_instance_node(node)

            created_instance = CreatedInstance.from_existing(node_data, self)
            self._add_instance_to_context(created_instance)

    def _default_update_instances(self, update_list):
        for created_inst, _changes in update_list:
            data = created_inst.data_to_store()
            node = data.get("instance_node")

            self.imprint_instance_node(node, data)

    def _default_remove_instances(self, instances):
        """Remove specified instance from the scene.

        This is only removing `id` parameter so instance is no longer
        instance, because it might contain valuable data for artist.

        """
        for instance in instances:
            node = instance.data.get("instance_node")
            if node:
                cmds.delete(node)

            self._remove_instance_from_context(instance)


@six.add_metaclass(ABCMeta)
class MayaCreator(NewCreator, MayaCreatorBase):

    settings_name = None

    def create(self, subset_name, instance_data, pre_create_data):

        members = list()
        if pre_create_data.get("use_selection"):
            members = cmds.ls(selection=True)

        # Allow a Creator to define multiple families
        publish_families = self.get_publish_families()
        if publish_families:
            families = instance_data.setdefault("families", [])
            for family in self.get_publish_families():
                if family not in families:
                    families.append(family)

        with lib.undo_chunk():
            instance_node = cmds.sets(members, name=subset_name)
            instance_data["instance_node"] = instance_node
            instance = CreatedInstance(
                self.family,
                subset_name,
                instance_data,
                self)
            self._add_instance_to_context(instance)

            self.imprint_instance_node(instance_node,
                                       data=instance.data_to_store())
            return instance

    def collect_instances(self):
        return self._default_collect_instances()

    def update_instances(self, update_list):
        return self._default_update_instances(update_list)

    def remove_instances(self, instances):
        return self._default_remove_instances(instances)

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection",
                    label="Use selection",
                    default=True)
        ]

    def apply_settings(self, project_settings):
        """Method called on initialization of plugin to apply settings."""

        settings_name = self.settings_name
        if settings_name is None:
            settings_name = self.__class__.__name__

        settings = project_settings["maya"]["create"]
        settings = settings.get(settings_name)
        if settings is None:
            self.log.debug(
                "No settings found for {}".format(self.__class__.__name__)
            )
            return

        for key, value in settings.items():
            setattr(self, key, value)


class MayaAutoCreator(AutoCreator, MayaCreatorBase):
    """Automatically triggered creator for Maya.

    The plugin is not visible in UI, and 'create' method does not expect
        any arguments.
    """

    def collect_instances(self):
        return self._default_collect_instances()

    def update_instances(self, update_list):
        return self._default_update_instances(update_list)

    def remove_instances(self, instances):
        return self._default_remove_instances(instances)


class MayaHiddenCreator(HiddenCreator, MayaCreatorBase):
    """Hidden creator for Maya.

    The plugin is not visible in UI, and it does not have strictly defined
        arguments for 'create' method.
    """

    def create(self, *args, **kwargs):
        return MayaCreator.create(self, *args, **kwargs)

    def collect_instances(self):
        return self._default_collect_instances()

    def update_instances(self, update_list):
        return self._default_update_instances(update_list)

    def remove_instances(self, instances):
        return self._default_remove_instances(instances)


def ensure_namespace(namespace):
    """Make sure the namespace exists.

    Args:
        namespace (str): The preferred namespace name.

    Returns:
        str: The generated or existing namespace

    """
    exists = cmds.namespace(exists=namespace)
    if exists:
        return namespace
    else:
        return cmds.namespace(add=namespace)


class RenderlayerCreator(NewCreator, MayaCreatorBase):
    """Creator which creates an instance per renderlayer in the workfile.

    Create and manages renderlayer subset per renderLayer in workfile.
    This generates a singleton node in the scene which, if it exists, tells the
    Creator to collect Maya rendersetup renderlayers as individual instances.
    As such, triggering create doesn't actually create the instance node per
    layer but only the node which tells the Creator it may now collect
    an instance per renderlayer.

    """

    # These are required to be overridden in subclass
    singleton_node_name = ""

    # These are optional to be overridden in subclass
    layer_instance_prefix = None

    def _get_singleton_node(self, return_all=False):
        nodes = lib.lsattr("pre_creator_identifier", self.identifier)
        if nodes:
            return nodes if return_all else nodes[0]

    def create(self, subset_name, instance_data, pre_create_data):
        # A Renderlayer is never explicitly created using the create method.
        # Instead, renderlayers from the scene are collected. Thus "create"
        # would only ever be called to say, 'hey, please refresh collect'
        self.create_singleton_node()

        # if no render layers are present, create default one with
        # asterisk selector
        rs = renderSetup.instance()
        if not rs.getRenderLayers():
            render_layer = rs.createRenderLayer("Main")
            collection = render_layer.createCollection("defaultCollection")
            collection.getSelector().setPattern('*')

        # By RenderLayerCreator.create we make it so that the renderlayer
        # instances directly appear even though it just collects scene
        # renderlayers. This doesn't actually 'create' any scene contents.
        self.collect_instances()

    def create_singleton_node(self):
        if self._get_singleton_node():
            raise CreatorError("A Render instance already exists - only "
                               "one can be configured.")

        with lib.undo_chunk():
            node = cmds.sets(empty=True, name=self.singleton_node_name)
            lib.imprint(node, data={
                "pre_creator_identifier": self.identifier
            })

        return node

    def collect_instances(self):

        # We only collect if the global render instance exists
        if not self._get_singleton_node():
            return

        rs = renderSetup.instance()
        layers = rs.getRenderLayers()
        for layer in layers:
            layer_instance_node = self.find_layer_instance_node(layer)
            if layer_instance_node:
                data = self.read_instance_node(layer_instance_node)
                instance = CreatedInstance.from_existing(data, creator=self)
            else:
                # No existing scene instance node for this layer. Note that
                # this instance will not have the `instance_node` data yet
                # until it's been saved/persisted at least once.
                project_name = self.create_context.get_current_project_name()

                instance_data = {
                    "asset": self.create_context.get_current_asset_name(),
                    "task": self.create_context.get_current_task_name(),
                    "variant": layer.name(),
                }
                asset_doc = get_asset_by_name(project_name,
                                              instance_data["asset"])
                subset_name = self.get_subset_name(
                    layer.name(),
                    instance_data["task"],
                    asset_doc,
                    project_name)

                instance = CreatedInstance(
                    family=self.family,
                    subset_name=subset_name,
                    data=instance_data,
                    creator=self
                )

            instance.transient_data["layer"] = layer
            self._add_instance_to_context(instance)

    def find_layer_instance_node(self, layer):
        connected_sets = cmds.listConnections(
            "{}.message".format(layer.name()),
            source=False,
            destination=True,
            type="objectSet"
        ) or []

        for node in connected_sets:
            if not cmds.attributeQuery("creator_identifier",
                                       node=node,
                                       exists=True):
                continue

            creator_identifier = cmds.getAttr(node + ".creator_identifier")
            if creator_identifier == self.identifier:
                self.log.info("Found node: {}".format(node))
                return node

    def _create_layer_instance_node(self, layer):

        # We only collect if a CreateRender instance exists
        create_render_set = self._get_singleton_node()
        if not create_render_set:
            raise CreatorError("Creating a renderlayer instance node is not "
                               "allowed if no 'CreateRender' instance exists")

        namespace = "_{}".format(self.singleton_node_name)
        namespace = ensure_namespace(namespace)

        name = "{}:{}".format(namespace, layer.name())
        render_set = cmds.sets(name=name, empty=True)

        # Keep an active link with the renderlayer so we can retrieve it
        # later by a physical maya connection instead of relying on the layer
        # name
        cmds.addAttr(render_set, longName="renderlayer", at="message")
        cmds.connectAttr("{}.message".format(layer.name()),
                         "{}.renderlayer".format(render_set), force=True)

        # Add the set to the 'CreateRender' set.
        cmds.sets(render_set, forceElement=create_render_set)

        return render_set

    def update_instances(self, update_list):
        # We only generate the persisting layer data into the scene once
        # we save with the UI on e.g. validate or publish
        for instance, _changes in update_list:
            instance_node = instance.data.get("instance_node")

            # Ensure a node exists to persist the data to
            if not instance_node:
                layer = instance.transient_data["layer"]
                instance_node = self._create_layer_instance_node(layer)
                instance.data["instance_node"] = instance_node

            self.imprint_instance_node(instance_node,
                                       data=instance.data_to_store())

    def imprint_instance_node(self, node, data):
        # Do not ever try to update the `renderlayer` since it'll try
        # to remove the attribute and recreate it but fail to keep it a
        # message attribute link. We only ever imprint that on the initial
        # node creation.
        # TODO: Improve how this is handled
        data.pop("renderlayer", None)
        data.get("creator_attributes", {}).pop("renderlayer", None)

        return super(RenderlayerCreator, self).imprint_instance_node(node,
                                                                     data=data)

    def remove_instances(self, instances):
        """Remove specified instances from the scene.

        This is only removing `id` parameter so instance is no longer
        instance, because it might contain valuable data for artist.

        """
        # Instead of removing the single instance or renderlayers we instead
        # remove the CreateRender node this creator relies on to decide whether
        # it should collect anything at all.
        nodes = self._get_singleton_node(return_all=True)
        if nodes:
            cmds.delete(nodes)

        # Remove ALL the instances even if only one gets deleted
        for instance in list(self.create_context.instances):
            if instance.get("creator_identifier") == self.identifier:
                self._remove_instance_from_context(instance)

                # Remove the stored settings per renderlayer too
                node = instance.data.get("instance_node")
                if node and cmds.objExists(node):
                    cmds.delete(node)

    def get_subset_name(
        self,
        variant,
        task_name,
        asset_doc,
        project_name,
        host_name=None,
        instance=None
    ):
        # creator.family != 'render' as expected
        return get_subset_name(self.layer_instance_prefix,
                               variant,
                               task_name,
                               asset_doc,
                               project_name)


class Loader(LoaderPlugin):
    hosts = ["maya"]

    load_settings = {}  # defined in settings

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        super(Loader, cls).apply_settings(project_settings, system_settings)
        cls.load_settings = project_settings['maya']['load']

    def get_custom_namespace_and_group(self, context, options, loader_key):
        """Queries Settings to get custom template for namespace and group.

        Group template might be empty >> this forces to not wrap imported items
        into separate group.

        Args:
            context (dict)
            options (dict): artist modifiable options from dialog
            loader_key (str): key to get separate configuration from Settings
                ('reference_loader'|'import_loader')
        """

        options["attach_to_root"] = True
        custom_naming = self.load_settings[loader_key]

        if not custom_naming['namespace']:
            raise LoadError("No namespace specified in "
                            "Maya ReferenceLoader settings")
        elif not custom_naming['group_name']:
            self.log.debug("No custom group_name, no group will be created.")
            options["attach_to_root"] = False

        asset = context['asset']
        subset = context['subset']
        formatting_data = {
            "asset_name": asset['name'],
            "asset_type": asset['type'],
            "folder": {
                "name": asset["name"],
            },
            "subset": subset['name'],
            "family": (
                subset['data'].get('family') or
                subset['data']['families'][0]
            )
        }

        custom_namespace = custom_naming['namespace'].format(
            **formatting_data
        )

        custom_group_name = custom_naming['group_name'].format(
            **formatting_data
        )

        return custom_group_name, custom_namespace, options


class ReferenceLoader(Loader):
    """A basic ReferenceLoader for Maya

    This will implement the basic behavior for a loader to inherit from that
    will containerize the reference and will implement the `remove` and
    `update` logic.

    """

    options = [
        qargparse.Integer(
            "count",
            label="Count",
            default=1,
            min=1,
            help="How many times to load?"
        ),
        qargparse.Double3(
            "offset",
            label="Position Offset",
            help="Offset loaded models for easier selection."
        ),
        qargparse.Boolean(
            "attach_to_root",
            label="Group imported asset",
            default=True,
            help="Should a group be created to encapsulate"
                 " imported representation ?"
        )
    ]

    def load(
        self,
        context,
        name=None,
        namespace=None,
        options=None
    ):
        path = self.filepath_from_context(context)
        assert os.path.exists(path), "%s does not exist." % path

        custom_group_name, custom_namespace, options = \
            self.get_custom_namespace_and_group(context, options,
                                                "reference_loader")

        count = options.get("count") or 1

        loaded_containers = []
        for c in range(0, count):
            namespace = lib.get_custom_namespace(custom_namespace)
            group_name = "{}:{}".format(
                namespace,
                custom_group_name
            )

            options['group_name'] = group_name

            # Offset loaded subset
            if "offset" in options:
                offset = [i * c for i in options["offset"]]
                options["translate"] = offset

            self.log.info(options)

            self.process_reference(
                context=context,
                name=name,
                namespace=namespace,
                options=options
            )

            # Only containerize if any nodes were loaded by the Loader
            nodes = self[:]
            if not nodes:
                return

            ref_node = lib.get_reference_node(nodes, self.log)
            container = containerise(
                name=name,
                namespace=namespace,
                nodes=[ref_node],
                context=context,
                loader=self.__class__.__name__
            )
            loaded_containers.append(container)
            self._organize_containers(nodes, container)
            c += 1

        return loaded_containers

    def process_reference(self, context, name, namespace, options):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def update(self, container, representation):
        from maya import cmds

        from openpype.hosts.maya.api.lib import get_container_members

        node = container["objectName"]

        path = get_representation_path(representation)

        # Get reference node from container members
        members = get_container_members(node)
        reference_node = lib.get_reference_node(members, self.log)
        namespace = cmds.referenceQuery(reference_node, namespace=True)

        file_type = {
            "ma": "mayaAscii",
            "mb": "mayaBinary",
            "abc": "Alembic",
            "fbx": "FBX"
        }.get(representation["name"])

        assert file_type, "Unsupported representation: %s" % representation

        assert os.path.exists(path), "%s does not exist." % path

        # Need to save alembic settings and reapply, cause referencing resets
        # them to incoming data.
        alembic_attrs = ["speed", "offset", "cycleType", "time"]
        alembic_data = {}
        if representation["name"] == "abc":
            alembic_nodes = cmds.ls(
                "{}:*".format(namespace), type="AlembicNode"
            )
            if alembic_nodes:
                for attr in alembic_attrs:
                    node_attr = "{}.{}".format(alembic_nodes[0], attr)
                    data = {
                        "input": lib.get_attribute_input(node_attr),
                        "value": cmds.getAttr(node_attr)
                    }

                    alembic_data[attr] = data
            else:
                self.log.debug("No alembic nodes found in {}".format(members))

        try:
            path = self.prepare_root_value(path,
                                           representation["context"]
                                                         ["project"]
                                                         ["name"])
            content = cmds.file(path,
                                loadReference=reference_node,
                                type=file_type,
                                returnNewNodes=True)
        except RuntimeError as exc:
            # When changing a reference to a file that has load errors the
            # command will raise an error even if the file is still loaded
            # correctly (e.g. when raising errors on Arnold attributes)
            # When the file is loaded and has content, we consider it's fine.
            if not cmds.referenceQuery(reference_node, isLoaded=True):
                raise

            content = cmds.referenceQuery(reference_node,
                                          nodes=True,
                                          dagPath=True)
            if not content:
                raise

            self.log.warning("Ignoring file read error:\n%s", exc)

        self._organize_containers(content, container["objectName"])

        # Reapply alembic settings.
        if representation["name"] == "abc" and alembic_data:
            alembic_nodes = cmds.ls(
                "{}:*".format(namespace), type="AlembicNode"
            )
            if alembic_nodes:
                alembic_node = alembic_nodes[0]  # assume single AlembicNode
                for attr, data in alembic_data.items():
                    node_attr = "{}.{}".format(alembic_node, attr)
                    input = lib.get_attribute_input(node_attr)
                    if data["input"]:
                        if data["input"] != input:
                            cmds.connectAttr(
                                data["input"], node_attr, force=True
                            )
                    else:
                        if input:
                            cmds.disconnectAttr(input, node_attr)
                        cmds.setAttr(node_attr, data["value"])

        # Fix PLN-40 for older containers created with Avalon that had the
        # `.verticesOnlySet` set to True.
        if cmds.getAttr("{}.verticesOnlySet".format(node)):
            self.log.info("Setting %s.verticesOnlySet to False", node)
            cmds.setAttr("{}.verticesOnlySet".format(node), False)

        # Remove any placeHolderList attribute entries from the set that
        # are remaining from nodes being removed from the referenced file.
        members = cmds.sets(node, query=True)
        invalid = [x for x in members if ".placeHolderList" in x]
        if invalid:
            cmds.sets(invalid, remove=node)

        # Update metadata
        cmds.setAttr("{}.representation".format(node),
                     str(representation["_id"]),
                     type="string")

        # When an animation or pointcache gets connected to an Xgen container,
        # the compound attribute "xgenContainers" gets created. When animation
        # containers gets updated we also need to update the cacheFileName on
        # the Xgen collection.
        compound_name = "xgenContainers"
        if cmds.objExists("{}.{}".format(node, compound_name)):
            import xgenm
            container_amount = cmds.getAttr(
                "{}.{}".format(node, compound_name), size=True
            )
            # loop through all compound children
            for i in range(container_amount):
                attr = "{}.{}[{}].container".format(node, compound_name, i)
                objectset = cmds.listConnections(attr)[0]
                reference_node = cmds.sets(objectset, query=True)[0]
                palettes = cmds.ls(
                    cmds.referenceQuery(reference_node, nodes=True),
                    type="xgmPalette"
                )
                for palette in palettes:
                    for description in xgenm.descriptions(palette):
                        xgenm.setAttr(
                            "cacheFileName",
                            path.replace("\\", "/"),
                            palette,
                            description,
                            "SplinePrimitive"
                        )

            # Refresh UI and viewport.
            de = xgenm.xgGlobal.DescriptionEditor
            de.refresh("Full")

    def remove(self, container):
        """Remove an existing `container` from Maya scene

        Deprecated; this functionality is replaced by `api.remove()`

        Arguments:
            container (openpype:container-1.0): Which container
                to remove from scene.

        """
        from maya import cmds

        node = container["objectName"]

        # Assume asset has been referenced
        members = cmds.sets(node, query=True)
        reference_node = lib.get_reference_node(members, self.log)

        assert reference_node, ("Imported container not supported; "
                                "container must be referenced.")

        self.log.info("Removing '%s' from Maya.." % container["name"])

        namespace = cmds.referenceQuery(reference_node, namespace=True)
        fname = cmds.referenceQuery(reference_node, filename=True)
        cmds.file(fname, removeReference=True)

        try:
            cmds.delete(node)
        except ValueError:
            # Already implicitly deleted by Maya upon removing reference
            pass

        try:
            # If container is not automatically cleaned up by May (issue #118)
            cmds.namespace(removeNamespace=namespace,
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass

    def prepare_root_value(self, file_url, project_name):
        """Replace root value with env var placeholder.

        Use ${OPENPYPE_ROOT_WORK} (or any other root) instead of proper root
        value when storing referenced url into a workfile.
        Useful for remote workflows with SiteSync.

        Args:
            file_url (str)
            project_name (dict)
        Returns:
            (str)
        """
        settings = get_project_settings(project_name)
        use_env_var_as_root = (settings["maya"]
                                       ["maya-dirmap"]
                                       ["use_env_var_as_root"])
        if use_env_var_as_root:
            anatomy = Anatomy(project_name)
            file_url = anatomy.replace_root_with_env_key(file_url, '${{{}}}')

        return file_url

    @staticmethod
    def _organize_containers(nodes, container):
        # type: (list, str) -> None
        """Put containers in loaded data to correct hierarchy."""
        for node in nodes:
            id_attr = "{}.id".format(node)
            if not cmds.attributeQuery("id", node=node, exists=True):
                continue
            if cmds.getAttr(id_attr) == AVALON_CONTAINER_ID:
                cmds.sets(node, forceElement=container)
