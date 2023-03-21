import os
import json
from abc import (
    ABCMeta
)
import six

from maya import cmds

import qargparse

from openpype.lib import Logger
from openpype.pipeline import (
    LoaderPlugin,
    get_representation_path,
    AVALON_CONTAINER_ID,
    Anatomy,
    LegacyCreator,
    Creator as NewCreator,
    CreatedInstance
)
from openpype.lib import BoolDef
from .lib import imprint, read

from openpype.settings import get_project_settings
from .pipeline import containerise
from . import lib


CREATOR_INSTANCE_ATTRS = {
    "id", "asset", "subset", "task", "variant", "family", "instance_id",
    "creator_identifier", "creator_attributes", "publish_attributes", "active"
}


def _get_attr(node, attr, default=None):
    """Helper to get attribute which allows attribute to not exist."""
    if not cmds.attributeQuery(attr, node=node, exists=True):
        return default
    return cmds.getAttr("{}.{}".format(node, attr))


def get_reference_node(members, log=None):
    """Get the reference node from the container members
    Args:
        members: list of node names

    Returns:
        str: Reference node name.

    """

    # Collect the references without .placeHolderList[] attributes as
    # unique entries (objects only) and skipping the sharedReferenceNode.
    references = set()
    for ref in cmds.ls(members, exactType="reference", objectsOnly=True):

        # Ignore any `:sharedReferenceNode`
        if ref.rsplit(":", 1)[-1].startswith("sharedReferenceNode"):
            continue

        # Ignore _UNKNOWN_REF_NODE_ (PLN-160)
        if ref.rsplit(":", 1)[-1].startswith("_UNKNOWN_REF_NODE_"):
            continue

        references.add(ref)

    assert references, "No reference node found in container"

    # Get highest reference node (least parents)
    highest = min(references,
                  key=lambda x: len(get_reference_node_parents(x)))

    # Warn the user when we're taking the highest reference node
    if len(references) > 1:
        if not log:
            log = Logger.get_logger(__name__)

        log.warning("More than one reference node found in "
                    "container, using highest reference node: "
                    "%s (in: %s)", highest, list(references))

    return highest


def get_reference_node_parents(ref):
    """Return all parent reference nodes of reference node

    Args:
        ref (str): reference node.

    Returns:
        list: The upstream parent reference nodes.

    """
    parent = cmds.referenceQuery(ref,
                                 referenceNode=True,
                                 parent=True)
    parents = []
    while parent:
        parents.append(parent)
        parent = cmds.referenceQuery(parent,
                                     referenceNode=True,
                                     parent=True)
    return parents


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

    def imprint_instance_node(self, node, data):

        # We never store the instance_node as value on the node since
        # it's the node name itself
        data.pop("instance_node", None)

        # We store creator attributes at the root level and assume they
        # will not clash in names with `subset`, `task`, etc. and other
        # default names. This is just so these attributes in many cases
        # are still editable in the maya UI by artists.
        data.update(data.pop("creator_attributes", {}))

        # We know the "publish_attributes" will be complex data of
        # settings per plugins, we'll store this as a flattened json structure
        publish_attributes = json.dumps(data.get("publish_attributes", {}))
        data.pop("publish_attributes", None)    # pop to move to end of dict
        data["publish_attributes"] = publish_attributes

        # Kill any existing attributes just we can imprint cleanly again
        for attr in data.keys():
            if cmds.attributeQuery(attr, node=node, exists=True):
                cmds.deleteAttr("{}.{}".format(node, attr))

        return imprint(node, data)

    def read_instance_node(self, node):
        node_data = read(node)

        # Never care about a cbId attribute on the object set
        # being read as 'data'
        node_data.pop("cbId", None)

        # Move the relevant attributes into "creator_attributes" that
        # we flattened originally
        node_data["creator_attributes"] = {}
        for key, value in node_data.items():
            if key not in CREATOR_INSTANCE_ATTRS:
                node_data["creator_attributes"][key] = value

        publish_attributes = node_data.get("publish_attributes")
        if publish_attributes:
            node_data["publish_attributes"] = json.loads(publish_attributes)

        # Explicitly re-parse the node name
        node_data["instance_node"] = node

        return node_data


@six.add_metaclass(ABCMeta)
class MayaCreator(NewCreator, MayaCreatorBase):

    def create(self, subset_name, instance_data, pre_create_data):

        members = list()
        if pre_create_data.get("use_selection"):
            members = cmds.ls(selection=True)

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
        self.cache_subsets(self.collection_shared_data)
        cached_subsets = self.collection_shared_data["maya_cached_subsets"]
        for node in cached_subsets.get(self.identifier, []):
            node_data = self.read_instance_node(node)

            created_instance = CreatedInstance.from_existing(node_data, self)
            self._add_instance_to_context(created_instance)

    def update_instances(self, update_list):
        for created_inst, _changes in update_list:
            data = created_inst.data_to_store()
            node = data.get("instance_node")

            self.imprint_instance_node(node, data)

    def remove_instances(self, instances):
        """Remove specified instance from the scene.

        This is only removing `id` parameter so instance is no longer
        instance, because it might contain valuable data for artist.

        """
        for instance in instances:
            node = instance.data.get("instance_node")
            if node:
                cmds.delete(node)

            self._remove_instance_from_context(instance)

    def get_pre_create_attr_defs(self):
        return [
            BoolDef("use_selection",
                    label="Use selection",
                    default=True)
        ]


class Loader(LoaderPlugin):
    hosts = ["maya"]


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
        assert os.path.exists(self.fname), "%s does not exist." % self.fname

        asset = context['asset']
        loaded_containers = []

        count = options.get("count") or 1
        for c in range(0, count):
            namespace = namespace or lib.unique_namespace(
                "{}_{}_".format(asset["name"], context["subset"]["name"]),
                prefix="_" if asset["name"][0].isdigit() else "",
                suffix="_",
            )

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

            ref_node = get_reference_node(nodes, self.log)
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
            namespace = None

        return loaded_containers

    def process_reference(self, context, name, namespace, data):
        """To be implemented by subclass"""
        raise NotImplementedError("Must be implemented by subclass")

    def update(self, container, representation):
        from maya import cmds
        from openpype.hosts.maya.api.lib import get_container_members

        node = container["objectName"]

        path = get_representation_path(representation)

        # Get reference node from container members
        members = get_container_members(node)
        reference_node = get_reference_node(members, self.log)
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
        reference_node = get_reference_node(members, self.log)

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
