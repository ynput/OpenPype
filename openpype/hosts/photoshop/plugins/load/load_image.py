import re

from avalon import api, photoshop

from openpype.hosts.photoshop.plugins.lib import get_unique_layer_name

stub = photoshop.stub()

class ImageLoader(api.Loader):
    """Load images

    Stores the imported asset in a container named after the asset.
    """

    families = ["image", "render"]
    representations = ["*"]

    def load(self, context, name=None, namespace=None, data=None):
        layer_name = get_unique_layer_name(stub.get_layers(),
                                           context["asset"]["name"],
                                           name)
        with photoshop.maintained_selection():
            layer = self.import_layer(self.fname, layer_name)

        self[:] = [layer]
        namespace = namespace or layer_name

        return photoshop.containerise(
            name,
            namespace,
            layer,
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
            layer_name = get_unique_layer_name(stub.get_layers(),
                                               context["asset"],
                                               context["subset"])
        else:  # switching version - keep same name
            layer_name = container["namespace"]

        path = api.get_representation_path(representation)
        with photoshop.maintained_selection():
            stub.replace_smart_object(
                layer, path, layer_name
            )

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

    def import_layer(self, file_name, layer_name):
        return stub.import_smart_object(file_name, layer_name)
