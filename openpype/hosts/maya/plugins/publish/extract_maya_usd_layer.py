import os

from maya import cmds
from openpype.pipeline import publish


class ExtractMayaUsdLayer(publish.Extractor):
    """Extractor for Maya USD Layer from `mayaUsdProxyShape`

    Exports a single Sdf.Layer from a mayaUsdPlugin `mayaUsdProxyShape`.
    These layers are the same managed via Maya's Windows > USD Layer Editor.

    """

    label = "Extract Maya USD Layer"
    hosts = ["maya"]
    families = ["mayaUsdLayer"]

    def process(self, instance):

        import mayaUsd

        # Load plugin first
        cmds.loadPlugin("mayaUsdPlugin", quiet=True)

        data = instance.data["stageLayerIdentifier"]
        proxy, layer_identifier = data.split(">", 1)

        # TODO: The stage and layer should actually be retrieved during
        #  Collecting so that they can be validated upon and potentially that
        #  any 'child layers' can potentially be recursively exported along
        stage = mayaUsd.ufe.getStage('|world' + proxy)
        layers = stage.GetLayerStack(includeSessionLayers=False)
        layer = next(
            layer for layer in layers if layer.identifier == layer_identifier
        )

        # Define output file path
        staging_dir = self.staging_dir(instance)
        file_name = "{0}.usd".format(instance.name)
        file_path = os.path.join(staging_dir, file_name)
        file_path = file_path.replace('\\', '/')

        self.log.debug("Exporting USD layer to: {}".format(file_path))
        layer.Export(file_path, args={
            "format": instance.data.get("defaultUSDFormat", "usdc")
        })

        # TODO: We might want to remap certain paths - to do so we could take
        #  the SdfLayer and transfer its contents into a anonymous SdfLayer
        #  then we can use the copy to alter it in memory to our like before
        #  writing out

        representation = {
            'name': "usd",
            'ext': "usd",
            'files': file_name,
            'stagingDir': staging_dir
        }
        instance.data.setdefault("representations", []).append(representation)
        self.log.debug(
            "Extracted instance {} to {}".format(instance.name, file_path)
        )
