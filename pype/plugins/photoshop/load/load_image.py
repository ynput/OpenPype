from avalon import api, photoshop

stub = photoshop.stub()


class ImageLoader(api.Loader):
    """Load images

    Stores the imported asset in a container named after the asset.
    """

    families = ["image"]
    representations = ["*"]

    def load(self, context, name=None, namespace=None, data=None):
        with photoshop.maintained_selection():
            layer = stub.import_smart_object(self.fname)

        self[:] = [layer]

        return photoshop.containerise(
            name,
            namespace,
            layer,
            context,
            self.__class__.__name__
        )

    def update(self, container, representation):
        layer = container.pop("layer")

        with photoshop.maintained_selection():
            stub.replace_smart_object(
                layer, api.get_representation_path(representation)
            )

        stub.imprint(
            layer, {"representation": str(representation["_id"])}
        )

    def remove(self, container):
        container["layer"].Delete()

    def switch(self, container, representation):
        self.update(container, representation)
