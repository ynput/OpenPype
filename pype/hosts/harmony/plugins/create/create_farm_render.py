# -*- coding: utf-8 -*-
"""Create Composite node for render on farm."""
from avalon import harmony


class CreateFarmRender(harmony.Creator):
    """Composite node for publishing renders."""

    name = "renderDefault"
    label = "Render on Farm"
    family = "renderFarm"
    node_type = "WRITE"

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(CreateFarmRender, self).__init__(*args, **kwargs)

    def setup_node(self, node):
        """Set render node."""
        path = "render/{0}/{0}.".format(node.split("/")[-1])
        harmony.send(
            {
                "function": f"PypeHarmony.Creators.CreateRender.create",
                "args": [node, path]
            })
        harmony.send(
            {
                "function": f"PypeHarmony.color",
                "args": [[0.9, 0.75, 0.3, 1.0]]
            }
        )
