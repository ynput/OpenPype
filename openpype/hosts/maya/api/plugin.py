import os

from maya import cmds

import qargparse

from avalon.pipeline import AVALON_CONTAINER_ID
from openpype.pipeline import (
    LegacyCreator,
    LoaderPlugin,
    get_representation_path,
)

from .pipeline import containerise
from . import lib


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
            from openpype.lib import PypeLogger

            log = PypeLogger().get_logger(__name__)

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
            "abc": "Alembic"
        }.get(representation["name"])

        assert file_type, "Unsupported representation: %s" % representation

        assert os.path.exists(path), "%s does not exist." % path

        # Need to save alembic settings and reapply, cause referencing resets
        # them to incoming data.
        alembic_attrs = ["speed", "offset", "cycleType"]
        alembic_data = {}
        if representation["name"] == "abc":
            alembic_nodes = cmds.ls(
                "{}:*".format(namespace), type="AlembicNode"
            )
            if alembic_nodes:
                for attr in alembic_attrs:
                    node_attr = "{}.{}".format(alembic_nodes[0], attr)
                    alembic_data[attr] = cmds.getAttr(node_attr)
            else:
                self.log.debug("No alembic nodes found in {}".format(members))

        try:
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
                for attr, value in alembic_data.items():
                    cmds.setAttr("{}.{}".format(alembic_nodes[0], attr), value)

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
