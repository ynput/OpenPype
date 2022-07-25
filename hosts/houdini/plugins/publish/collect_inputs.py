import pyblish.api

from openpype.pipeline import registered_host


def collect_input_containers(nodes):
    """Collect containers that contain any of the node in `nodes`.

    This will return any loaded Avalon container that contains at least one of
    the nodes. As such, the Avalon container is an input for it. Or in short,
    there are member nodes of that container.

    Returns:
        list: Input avalon containers

    """

    # Lookup by node ids
    lookup = frozenset(nodes)

    containers = []
    host = registered_host()
    for container in host.ls():

        node = container["node"]

        # Usually the loaded containers don't have any complex references
        # and the contained children should be all we need. So we disregard
        # checking for .references() on the nodes.
        members = set(node.allSubChildren())
        members.add(node)  # include the node itself

        # If there's an intersection
        if not lookup.isdisjoint(members):
            containers.append(container)

    return containers


def iter_upstream(node):
    """Yields all upstream inputs for the current node.

    This includes all `node.inputAncestors()` but also traverses through all
    `node.references()` for the node itself and for any of the upstream nodes.
    This method has no max-depth and will collect all upstream inputs.

    Yields:
        hou.Node: The upstream nodes, including references.

    """

    upstream = node.inputAncestors(
        include_ref_inputs=True, follow_subnets=True
    )

    # Initialize process queue with the node's ancestors itself
    queue = list(upstream)
    collected = set(upstream)

    # Traverse upstream references for all nodes and yield them as we
    # process the queue.
    while queue:
        upstream_node = queue.pop()
        yield upstream_node

        # Find its references that are not collected yet.
        references = upstream_node.references()
        references = [n for n in references if n not in collected]

        queue.extend(references)
        collected.update(references)

        # Include the references' ancestors that have not been collected yet.
        for reference in references:
            ancestors = reference.inputAncestors(
                include_ref_inputs=True, follow_subnets=True
            )
            ancestors = [n for n in ancestors if n not in collected]

            queue.extend(ancestors)
            collected.update(ancestors)


class CollectUpstreamInputs(pyblish.api.InstancePlugin):
    """Collect source input containers used for this publish.

    This will include `inputs` data of which loaded publishes were used in the
    generation of this publish. This leaves an upstream trace to what was used
    as input.

    """

    label = "Collect Inputs"
    order = pyblish.api.CollectorOrder + 0.4
    hosts = ["houdini"]

    def process(self, instance):
        # We can't get the "inputAncestors" directly from the ROP
        # node, so we find the related output node (set in SOP/COP path)
        # and include that together with its ancestors
        output = instance.data.get("output_node")

        if output is None:
            # If no valid output node is set then ignore it as validation
            # will be checking those cases.
            self.log.debug(
                "No output node found, skipping " "collecting of inputs.."
            )
            return

        # Collect all upstream parents
        nodes = list(iter_upstream(output))
        nodes.append(output)

        # Collect containers for the given set of nodes
        containers = collect_input_containers(nodes)

        inputs = [c["representation"] for c in containers]
        instance.data["inputs"] = inputs

        self.log.info("Collected inputs: %s" % inputs)
