import pyblish.api

from openpype.pipeline import registered_host


def collect_input_containers(tools):
    """Collect containers that contain any of the node in `nodes`.

    This will return any loaded Avalon container that contains at least one of
    the nodes. As such, the Avalon container is an input for it. Or in short,
    there are member nodes of that container.

    Returns:
        list: Input avalon containers

    """

    # Lookup by node ids
    lookup = frozenset([tool.Name for tool in tools])

    containers = []
    host = registered_host()
    for container in host.ls():

        name = container["_tool"].Name

        # We currently assume no "groups" as containers but just single tools
        # like a single "Loader" operator. As such we just check whether the
        # Loader is part of the processing queue.
        if name in lookup:
            containers.append(container)

    return containers


def iter_upstream(tool):
    """Yields all upstream inputs for the current tool.

    Yields:
        tool: The input tools.

    """

    def get_connected_input_tools(tool):
        """Helper function that returns connected input tools for a tool."""
        inputs = []

        # Filter only to actual types that will have sensible upstream
        # connections. So we ignore just "Number" inputs as they can be
        # many to iterate, slowing things down quite a bit - and in practice
        # they don't have upstream connections.
        VALID_INPUT_TYPES = ['Image', 'Particles', 'Mask', 'DataType3D']
        for type_ in VALID_INPUT_TYPES:
            for input_ in tool.GetInputList(type_).values():
                output = input_.GetConnectedOutput()
                if output:
                    input_tool = output.GetTool()
                    inputs.append(input_tool)

        return inputs

    # Initialize process queue with the node's inputs itself
    queue = get_connected_input_tools(tool)

    # We keep track of which node names we have processed so far, to ensure we
    # don't process the same hierarchy again. We are not pushing the tool
    # itself into the set as that doesn't correctly recognize the same tool.
    # Since tool names are unique in a comp in Fusion we rely on that.
    collected = set(tool.Name for tool in queue)

    # Traverse upstream references for all nodes and yield them as we
    # process the queue.
    while queue:
        upstream_tool = queue.pop()
        yield upstream_tool

        # Find upstream tools that are not collected yet.
        upstream_inputs = get_connected_input_tools(upstream_tool)
        upstream_inputs = [t for t in upstream_inputs if
                           t.Name not in collected]

        queue.extend(upstream_inputs)
        collected.update(tool.Name for tool in upstream_inputs)


class CollectUpstreamInputs(pyblish.api.InstancePlugin):
    """Collect source input containers used for this publish.

    This will include `inputs` data of which loaded publishes were used in the
    generation of this publish. This leaves an upstream trace to what was used
    as input.

    """

    label = "Collect Inputs"
    order = pyblish.api.CollectorOrder + 0.2
    hosts = ["fusion"]
    families = ["render", "image"]

    def process(self, instance):

        # Get all upstream and include itself
        if not any(instance[:]):
            self.log.debug("No tool found in instance, skipping..")
            return

        tool = instance[0]
        nodes = list(iter_upstream(tool))
        nodes.append(tool)

        # Collect containers for the given set of nodes
        containers = collect_input_containers(nodes)

        inputs = [c["representation"] for c in containers]
        instance.data["inputRepresentations"] = inputs
        self.log.debug("Collected inputs: %s" % inputs)
