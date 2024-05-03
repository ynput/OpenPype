import re
import platform
import subprocess

from pathlib import Path

from openpype.pipeline import get_representation_path
from openpype.hosts.aftereffects import api
from openpype.hosts.aftereffects.api.lib import get_unique_layer_name


class FileLoader(api.AfterEffectsLoader):
    """Load images

    Stores the imported asset in a container named after the asset.
    """
    label = "Load file"

    families = ["image",
                "plate",
                "render",
                "prerender",
                "review",
                "audio",
                "workfile"]
    representations = ["*"]

    def load(self, context, name=None, namespace=None, data=None):
        stub = self.get_stub()
        layers = stub.get_items(comps=True, folders=True, footages=True)
        existing_layers = [layer.name for layer in layers]
        comp_name = get_unique_layer_name(
            existing_layers, "{}_{}".format(context["asset"]["name"], name))

        import_options = {}

        path = self.filepath_from_context(context)
        repr_cont = context["representation"]["context"]

        if len(context["representation"]["files"]) > 1:
            import_options['sequence'] = True

        if not path:
            repr_id = context["representation"]["_id"]
            self.log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return

        path = path.replace("\\", "/")

        frame = None
        if '.psd' in path:
            import_options['ImportAsType'] = 'ImportAsType.COMP'
            comp = stub.import_file_with_dialog(
                path,
                stub.LOADED_ICON + comp_name,
                import_options
            )
        else:
            frame = repr_cont.get("frame")
            if frame:
                import_options['sequence'] = True

            comp = stub.import_file(
                path,
                stub.LOADED_ICON + comp_name,
                import_options
            )

        if not comp:
            if frame:
                padding = len(frame)
                path = path.replace(frame, "#" * padding)

            self.log.warning(
                "Representation `{}` is failing to load".format(path))
            self.log.warning("Check host app for alert error.")

            return

        self[:] = [comp]
        namespace = namespace or comp_name

        return api.containerise(
            name,
            namespace,
            comp,
            context,
            self.__class__.__name__
        )

    def update(self, container, representation):
        """ Switch asset or change version """
        stub = self.get_stub()
        layer = container.pop("layer")

        context = representation.get("context", {})

        namespace_from_container = re.sub(r'_\d{3}$', '',
                                          container["namespace"])
        layer_name = "{}_{}".format(context["asset"], context["subset"])
        # switching assets
        if namespace_from_container != layer_name:
            layers = stub.get_items(comps=True)
            existing_layers = [layer.name for layer in layers]
            layer_name = get_unique_layer_name(
                existing_layers,
                "{}_{}".format(context["asset"], context["subset"]))
        else:  # switching version - keep same name
            layer_name = container["namespace"]
        path = get_representation_path(representation)
        # with aftereffects.maintained_selection():  # TODO

        # Convert into a Path object
        path = Path(path)

        # Resolve and then get a string
        path_str = str(path.resolve())

        stub.replace_item(layer.id, path_str, stub.LOADED_ICON + layer_name)
        stub.imprint(
            layer.id, {"representation": str(representation["_id"]),
                       "name": context["subset"],
                       "namespace": layer_name}
        )

    def remove(self, container):
        """
            Removes element from scene: deletes layer + removes from Headline
        Args:
            container (dict): container to be removed - used to get layer_id
        """
        stub = self.get_stub()
        layer = container.pop("layer")
        stub.imprint(layer.id, {})
        stub.delete_item(layer.id)

    def switch(self, container, representation):
        self.update(container, representation)
