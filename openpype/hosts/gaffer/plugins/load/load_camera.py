from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.gaffer.api import get_root, imprint_container
from openpype.hosts.gaffer.api.lib import set_node_color, arrange, make_box

import Gaffer
import GafferScene
import IECore


class GafferLoadAlembicCamera(load.LoaderPlugin):
    """Load Alembic Camera"""

    families = ["camera"]
    representations = ["abc"]

    label = "Load camera"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):
        # Create the Loader with the filename path set
        script = get_root()

        # Due to an open issue to be implemented for Alembic we need to
        # manually assign the camera into Gaffer's '__cameras' set. So for
        # now we encapsulate what's needed in a Box node to resolve that.
        # See: https://github.com/GafferHQ/gaffer/issues/3954
        box = make_box(name, add_input=False)
        reader = GafferScene.SceneReader()
        box.addChild(reader)

        create_set = GafferScene.Set("cameras_set")
        box.addChild(create_set)
        create_set["name"].setValue("__cameras")
        create_set["in"].setInput(reader["out"])

        path_filter = GafferScene.PathFilter("all")
        box.addChild(path_filter)
        path_filter["paths"].setValue(IECore.StringVectorData(["*"]))
        create_set["filter"].setInput(path_filter["out"])

        box["BoxOut"]["in"].setInput(create_set["out"])

        script.addChild(box)

        # Promote the reader's filename directly to the box
        Gaffer.PlugAlgo.promote(reader["fileName"])

        # Set the filename
        path = self.fname.replace("\\", "/")
        box["fileName"].setValue(path)

        # Layout the nodes within the box
        arrange(box.children(Gaffer.Node))

        # Colorize based on family
        # TODO: Use settings instead
        set_node_color(box, (0.533, 0.447, 0.957))

        imprint_container(box,
                          name=name,
                          namespace=namespace,
                          context=context,
                          loader=self.__class__.__name__)

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):

        path = get_representation_path(representation)
        path = path.replace("\\", "/")

        node = container["_node"]
        node["fileName"].setValue(path)

        # Update the imprinted representation
        node["user"]["representation"].SetValue(str(representation["_id"]))

    def remove(self, container):
        node = container["_node"]

        parent = node.parent()
        parent.removeChild(node)
