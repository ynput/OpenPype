from avalon import api, aftereffects
from pype.plugins import lib
import re

stub = aftereffects.stub()


class ImageLoader(api.Loader):
    """Load images

    Stores the imported asset in a container named after the asset.
    """

    families = ["image"]
    representations = ["*"]

    def load(self, context, name=None, namespace=None, data=None):
        print("Load:::")
        layer_name = lib.get_unique_layer_name(stub.get_items(False),
                                               context["asset"]["name"],
                                               name)
        #with photoshop.maintained_selection():
        comp = stub.import_file(self.fname, layer_name)

        self[:] = [comp]
        namespace = namespace or layer_name

        return aftereffects.containerise(
            name,
            namespace,
            comp,
            context,
            self.__class__.__name__
        )

    def update(self, container, representation):
        """ Switch asset or change version """
        layer = container.pop("layer")

        context = representation.get("context", {})

        namespace_from_container = re.sub(r'_\d{3}$', '',
                                          container["namespace"])
        layer_name = "{}_{}".format(context["asset"], context["subset"])
        # switching assets
        if namespace_from_container != layer_name:
            layer_name = lib.get_unique_layer_name(stub.get_items(False),
                                                   context["asset"],
                                                   context["subset"])
        else:  # switching version - keep same name
            layer_name = container["namespace"]
        path = api.get_representation_path(representation)
        # with aftereffects.maintained_selection():  # TODO
        stub.replace_item(layer, path, layer_name)
        stub.imprint(
            layer, {"representation": str(representation["_id"])}
        )

    def remove(self, container):
        """
            Removes element from scene: deletes layer + removes from Headline
        Args:
            container (dict): container to be removed - used to get layer_id
        """
        layer = container.pop("layer")
        stub.imprint(layer, {})
        stub.delete_layer(layer.id)

    def switch(self, container, representation):
        self.update(container, representation)


