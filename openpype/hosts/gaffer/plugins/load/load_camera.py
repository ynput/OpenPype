from openpype.pipeline import (
    load,
    get_representation_path,
)
from openpype.hosts.gaffer.api import get_root, imprint_container

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

        node = GafferScene.SceneReader()
        node.setName(name)

        path = self.fname.replace("\\", "/")
        node["fileName"].setValue(path)
        script.addChild(node)

        # Due to an open issue to be implemented for Alembic we need to
        # manually assign the camera into Gaffer's '__cameras' set.
        # todo: implement name updating + correct deleting on remove, etc.
        camera_name = "/" + str(node["out"].childNames("/")[0])
        create_set = GafferScene.Set()
        script.addChild(create_set)
        create_set["name"].setValue("__cameras")
        create_set["paths"].setValue(IECore.StringVectorData([camera_name]))
        create_set["in"].setInput(node["out"])
        create_set.setName("{}_set".format(name))

        imprint_container(node,
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