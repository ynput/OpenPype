# Photoshop Integration

## Setup

The Photoshop integration requires two components to work; `extension` and `server`.

### Extension

To install the extension download [Extension Manager Command Line tool (ExManCmd)](https://github.com/Adobe-CEP/Getting-Started-guides/tree/master/Package%20Distribute%20Install#option-2---exmancmd).

```
ExManCmd /install {path to avalon-core}\avalon\photoshop\extension.zxp
```

### Server

The easiest way to get the server and Photoshop launch is with:

```
python -c ^"import avalon.photoshop;avalon.photoshop.launch(""C:\Program Files\Adobe\Adobe Photoshop 2020\Photoshop.exe"")^"
```

`avalon.photoshop.launch` launches the application and server, and also closes the server when Photoshop exists.

## Usage

The Photoshop extension can be found under `Window > Extensions > Avalon`. Once launched you should be presented with a panel like this:

![Avalon Panel](panel.PNG "Avalon Panel")


## Developing

### Extension
When developing the extension you can load it [unsigned](https://github.com/Adobe-CEP/CEP-Resources/blob/master/CEP_9.x/Documentation/CEP%209.0%20HTML%20Extension%20Cookbook.md#debugging-unsigned-extensions).

When signing the extension you can use this [guide](https://github.com/Adobe-CEP/Getting-Started-guides/tree/master/Package%20Distribute%20Install#package-distribute-install-guide).

```
ZXPSignCmd -selfSignedCert NA NA Avalon Avalon-Photoshop avalon extension.p12
ZXPSignCmd -sign {path to avalon-core}\avalon\photoshop\extension {path to avalon-core}\avalon\photoshop\extension.zxp extension.p12 avalon
```

### Plugin Examples

These plugins were made with the [polly config](https://github.com/mindbender-studio/config). To fully integrate and load, you will have to use this config and add `image` to the [integration plugin](https://github.com/mindbender-studio/config/blob/master/polly/plugins/publish/integrate_asset.py).

#### Creator Plugin
```python
from avalon import photoshop


class CreateImage(photoshop.Creator):
    """Image folder for publish."""

    name = "imageDefault"
    label = "Image"
    family = "image"

    def __init__(self, *args, **kwargs):
        super(CreateImage, self).__init__(*args, **kwargs)
```

#### Collector Plugin
```python
import pythoncom

import pyblish.api


class CollectInstances(pyblish.api.ContextPlugin):
    """Gather instances by LayerSet and file metadata

    This collector takes into account assets that are associated with
    an LayerSet and marked with a unique identifier;

    Identifier:
        id (str): "pyblish.avalon.instance"
    """

    label = "Instances"
    order = pyblish.api.CollectorOrder
    hosts = ["photoshop"]
    families_mapping = {
        "image": []
    }

    def process(self, context):
        # Necessary call when running in a different thread which pyblish-qml
        # can be.
        pythoncom.CoInitialize()

        photoshop_client = PhotoshopClientStub()
        layers = photoshop_client.get_layers()
        layers_meta = photoshop_client.get_layers_metadata()
        for layer in layers:
            layer_data = photoshop_client.read(layer, layers_meta)

            # Skip layers without metadata.
            if layer_data is None:
                continue

            # Skip containers.
            if "container" in layer_data["id"]:
                continue

            # child_layers = [*layer.Layers]
            # self.log.debug("child_layers {}".format(child_layers))
            # if not child_layers:
            #     self.log.info("%s skipped, it was empty." % layer.Name)
            #     continue

            instance = context.create_instance(layer.name)
            instance.append(layer)
            instance.data.update(layer_data)
            instance.data["families"] = self.families_mapping[
                layer_data["family"]
            ]
            instance.data["publish"] = layer.visible

            # Produce diagnostic message for any graphical
            # user interface interested in visualising it.
            self.log.info("Found: \"%s\" " % instance.data["name"])
```

#### Extractor Plugin
```python
import os

import openpype.api
from avalon import photoshop


class ExtractImage(openpype.api.Extractor):
    """Produce a flattened image file from instance

    This plug-in takes into account only the layers in the group.
    """

    label = "Extract Image"
    hosts = ["photoshop"]
    families = ["image"]
    formats = ["png", "jpg"]

    def process(self, instance):

        staging_dir = self.staging_dir(instance)
        self.log.info("Outputting image to {}".format(staging_dir))

        # Perform extraction
        stub = photoshop.stub()
        files = {}
        with photoshop.maintained_selection():
            self.log.info("Extracting %s" % str(list(instance)))
            with photoshop.maintained_visibility():
                # Hide all other layers.
                extract_ids = set([ll.id for ll in stub.
                                   get_layers_in_layers([instance[0]])])

                for layer in stub.get_layers():
                    # limit unnecessary calls to client
                    if layer.visible and layer.id not in extract_ids:
                        stub.set_visible(layer.id, False)

                save_options = []
                if "png" in self.formats:
                    save_options.append('png')
                if "jpg" in self.formats:
                    save_options.append('jpg')

                file_basename = os.path.splitext(
                    stub.get_active_document_name()
                )[0]
                for extension in save_options:
                    _filename = "{}.{}".format(file_basename, extension)
                    files[extension] = _filename

                    full_filename = os.path.join(staging_dir, _filename)
                    stub.saveAs(full_filename, extension, True)

        representations = []
        for extension, filename in files.items():
            representations.append({
                "name": extension,
                "ext": extension,
                "files": filename,
                "stagingDir": staging_dir
            })
        instance.data["representations"] = representations
        instance.data["stagingDir"] = staging_dir

        self.log.info(f"Extracted {instance} to {staging_dir}")
```

#### Loader Plugin
```python
from avalon import api, photoshop
from openpype.pipeline import load, get_representation_path

stub = photoshop.stub()


class ImageLoader(load.LoaderPlugin):
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
                layer, get_representation_path(representation)
            )

        stub.imprint(
            layer, {"representation": str(representation["_id"])}
        )

    def remove(self, container):
        container["layer"].Delete()

    def switch(self, container, representation):
        self.update(container, representation)
```
For easier debugging of Javascript:
https://community.adobe.com/t5/download-install/adobe-extension-debuger-problem/td-p/10911704?page=1
Add --enable-blink-features=ShadowDOMV0,CustomElementsV0 when starting Chrome
then localhost:8078 (port set in `photoshop\extension\.debug`)

Or use Visual Studio Code https://medium.com/adobetech/extendscript-debugger-for-visual-studio-code-public-release-a2ff6161fa01

Or install CEF client from https://github.com/Adobe-CEP/CEP-Resources/tree/master/CEP_9.x
## Resources
  - https://github.com/lohriialo/photoshop-scripting-python
  - https://www.adobe.com/devnet/photoshop/scripting.html
  - https://github.com/Adobe-CEP/Getting-Started-guides
  - https://github.com/Adobe-CEP/CEP-Resources
