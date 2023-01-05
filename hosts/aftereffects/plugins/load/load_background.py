import re

from openpype.lib import (
    get_background_layers,
    get_unique_layer_name
)
from openpype.pipeline import get_representation_path
from openpype.hosts.aftereffects.api import (
    AfterEffectsLoader,
    containerise
)


class BackgroundLoader(AfterEffectsLoader):
    """
        Load images from Background family
        Creates for each background separate folder with all imported images
        from background json AND automatically created composition with layers,
        each layer for separate image.

        For each load container is created and stored in project (.aep)
        metadata
    """
    families = ["background"]
    representations = ["json"]

    def load(self, context, name=None, namespace=None, data=None):
        stub = self.get_stub()
        items = stub.get_items(comps=True)
        existing_items = [layer.name.replace(stub.LOADED_ICON, '')
                          for layer in items]

        comp_name = get_unique_layer_name(
            existing_items,
            "{}_{}".format(context["asset"]["name"], name))

        layers = get_background_layers(self.fname)
        if not layers:
            raise ValueError("No layers found in {}".format(self.fname))

        comp = stub.import_background(None, stub.LOADED_ICON + comp_name,
                                      layers)

        if not comp:
            raise ValueError("Import background failed. "
                             "Please contact support")

        self[:] = [comp]
        namespace = namespace or comp_name

        return containerise(
            name,
            namespace,
            comp,
            context,
            self.__class__.__name__
        )

    def update(self, container, representation):
        """ Switch asset or change version """
        stub = self.get_stub()
        context = representation.get("context", {})
        _ = container.pop("layer")

        # without iterator number (_001, 002...)
        namespace_from_container = re.sub(r'_\d{3}$', '',
                                          container["namespace"])
        comp_name = "{}_{}".format(context["asset"], context["subset"])

        # switching assets
        if namespace_from_container != comp_name:
            items = stub.get_items(comps=True)
            existing_items = [layer.name for layer in items]
            comp_name = get_unique_layer_name(
                existing_items,
                "{}_{}".format(context["asset"], context["subset"]))
        else:  # switching version - keep same name
            comp_name = container["namespace"]

        path = get_representation_path(representation)

        layers = get_background_layers(path)
        comp = stub.reload_background(container["members"][1],
                                      stub.LOADED_ICON + comp_name,
                                      layers)

        # update container
        container["representation"] = str(representation["_id"])
        container["name"] = context["subset"]
        container["namespace"] = comp_name
        container["members"] = comp.members

        stub.imprint(comp.id, container)

    def remove(self, container):
        """
            Removes element from scene: deletes layer + removes from file
            metadata.
        Args:
            container (dict): container to be removed - used to get layer_id
        """
        stub = self.get_stub()
        layer = container.pop("layer")
        stub.imprint(layer.id, {})
        stub.delete_item(layer.id)

    def switch(self, container, representation):
        self.update(container, representation)
