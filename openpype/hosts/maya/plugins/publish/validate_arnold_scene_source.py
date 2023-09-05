import pyblish.api

from openpype.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidateContentsOrder,
)


class ValidateArnoldSceneSource(pyblish.api.InstancePlugin,
                                OptionalPyblishPluginMixin):
    """Validate Arnold Scene Source.

    We require at least 1 root node/parent for the meshes. This is to ensure we
    can duplicate the nodes and preserve the names.

    If using proxies we need the nodes to share the same names and not be
    parent to the world. This ends up needing at least two groups with content
    nodes and proxy nodes in another.
    """

    order = ValidateContentsOrder
    hosts = ["maya"]
    families = ["ass"]
    label = "Validate Arnold Scene Source"

    def _get_nodes_by_name(self, nodes):
        ungrouped_nodes = []
        nodes_by_name = {}
        parents = []
        same_named_nodes = {}
        for node in nodes:
            node_split = node.split("|")
            if len(node_split) == 2:
                ungrouped_nodes.append(node)

            parent = "|".join(node_split[:-1])
            if parent:
                parents.append(parent)

            node_name = node.rsplit("|", 1)[-1].rsplit(":", 1)[-1]

            # Check for same same nodes, which can happen in different
            # hierarchies.
            if node_name in nodes_by_name:
                try:
                    same_named_nodes[node_name].append(node)
                except KeyError:
                    same_named_nodes[node_name] = [
                        nodes_by_name[node_name], node
                    ]

            nodes_by_name[node_name] = node

        if same_named_nodes:
            message = "Found nodes with the same name:"
            for name, nodes in same_named_nodes.items():
                message += "\n\n\"{}\":\n{}".format(name, "\n".join(nodes))

            raise PublishValidationError(message)

        return ungrouped_nodes, nodes_by_name, parents

    def process(self, instance):
        ungrouped_nodes = []

        nodes, content_nodes_by_name, content_parents = (
            self._get_nodes_by_name(instance.data["contentMembers"])
        )
        ungrouped_nodes.extend(nodes)

        nodes, proxy_nodes_by_name, proxy_parents = self._get_nodes_by_name(
            instance.data.get("proxy", [])
        )
        ungrouped_nodes.extend(nodes)

        # Validate against nodes directly parented to world.
        if ungrouped_nodes:
            raise PublishValidationError(
                "Found nodes parented to the world: {}\n"
                "All nodes need to be grouped.".format(ungrouped_nodes)
            )

        # Proxy validation.
        if not instance.data.get("proxy", []):
            return

        # Validate for content and proxy nodes amount being the same.
        if len(instance.data["contentMembers"]) != len(instance.data["proxy"]):
            raise PublishValidationError(
                "Amount of content nodes ({}) and proxy nodes ({}) needs to "
                "be the same.".format(
                    len(instance.data["contentMembers"]),
                    len(instance.data["proxy"])
                )
            )

        # Validate against content and proxy nodes sharing same parent.
        if list(set(content_parents) & set(proxy_parents)):
            raise PublishValidationError(
                "Content and proxy nodes cannot share the same parent."
            )

        # Validate for content and proxy nodes sharing same names.
        sorted_content_names = sorted(content_nodes_by_name.keys())
        sorted_proxy_names = sorted(proxy_nodes_by_name.keys())
        odd_content_names = list(
            set(sorted_content_names) - set(sorted_proxy_names)
        )
        odd_content_nodes = [
            content_nodes_by_name[x] for x in odd_content_names
        ]
        odd_proxy_names = list(
            set(sorted_proxy_names) - set(sorted_content_names)
        )
        odd_proxy_nodes = [
            proxy_nodes_by_name[x] for x in odd_proxy_names
        ]
        if not sorted_content_names == sorted_proxy_names:
            raise PublishValidationError(
                "Content and proxy nodes need to share the same names.\n"
                "Content nodes not matching: {}\n"
                "Proxy nodes not matching: {}".format(
                    odd_content_nodes, odd_proxy_nodes
                )
            )
