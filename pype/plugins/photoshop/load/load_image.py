from avalon import api, photoshop
import os
import re

stub = photoshop.stub()


class ImageLoader(api.Loader):
    """Load images

    Stores the imported asset in a container named after the asset.
    """

    families = ["image", "render"]
    representations = ["*"]

    def load(self, context, name=None, namespace=None, data=None):
        layer_name = self._get_unique_layer_name(context["asset"]["name"],
                                                 name)
        with photoshop.maintained_selection():
            layer = stub.import_smart_object(self.fname, layer_name)

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
            layer_name = self._get_unique_layer_name(context["asset"],
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

    def _get_unique_layer_name(self, asset_name, subset_name):
        """
            Gets all layer names and if 'name' is present in them, increases
            suffix by 1 (eg. creates unique layer name - for Loader)
        Args:
            name (string):  in format asset_subset

        Returns:
            (string): name_00X (without version)
        """
        name = "{}_{}".format(asset_name, subset_name)
        names = {}
        for layer in stub.get_layers():
            layer_name = re.sub(r'_\d{3}$', '', layer.name)
            if layer_name in names.keys():
                names[layer_name] = names[layer_name] + 1
            else:
                names[layer_name] = 1
        occurrences = names.get(name, 0)

        return "{}_{:0>3d}".format(name, occurrences + 1)
