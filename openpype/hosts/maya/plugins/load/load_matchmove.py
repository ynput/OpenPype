# -*- coding: utf-8 -*-
from maya import cmds, mel  # noqa: F401

from openpype.hosts.maya.api.pipeline import containerise
from openpype.hosts.maya.api import lib, Loader
from openpype.pipeline.load import get_representation_path, LoadError


class MatchmoveLoader(Loader):
    """Run matchmove script to create track in scene.

    Supported script types are .py and .mel

    TODO: there might be error in the scripts exported from
          3DEqualizer that it is trying to set frame attribute
          on camera image plane and then add expression for
          image sequence. Maya will throw RuntimeError at that
          point that will stop processing rest of the script and
          the container will not be created. We should somehow handle
          this - maybe even by patching the mel script on-the-fly.

    """

    families = ["matchmove"]
    representations = ["py", "mel"]
    defaults = ["Camera", "Object", "Mocap"]

    label = "Run matchmove script"
    icon = "empire"
    color = "orange"

    def load(self, context, name, namespace, options):

        path = self.filepath_from_context(context)
        custom_group_name, custom_namespace, options = \
            self.get_custom_namespace_and_group(
                context, options, "matchmove_loader")

        namespace = lib.get_custom_namespace(custom_namespace)

        nodes = self._load_nodes_from_script(path)

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__
        )

    def update(self, container, representation):
        # type: (dict, dict) -> None
        """Update container with specified representation."""
        self.remove(container)

        path = get_representation_path(representation)
        namespace = container["namespace"]
        print(f">>> loading from {path}")
        try:
            nodes = self._load_nodes_from_script(path)
        except RuntimeError as e:
            raise LoadError("Failed to load matchmove script.") from e

        return containerise(
            name=container["name"],
            namespace=namespace,
            nodes=nodes,
            context=representation["context"],
            loader=self.__class__.__name__
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        """Delete container and its contents."""

        if cmds.objExists(container['objectName']):
            members = cmds.sets(container['objectName'], query=True) or []
            cmds.delete([container['objectName']] + members)

    def _load_nodes_from_script(self, path):
        # type: (str) -> list
        """Load nodes from script.

        This will execute py or mel script and resulting
        nodes will be returned.

        Args:
            path (str): path to script

        Returns:
            list: list of created nodes

        """
        previous_nodes = set(cmds.ls(long=True))

        if path.lower().endswith(".py"):
            exec(open(path).read())

        elif path.lower().endswith(".mel"):
            mel.eval(open(path).read())

        else:
            self.log.error("Unsupported script type")

        current_nodes = set(cmds.ls(long=True))
        return list(current_nodes - previous_nodes)
