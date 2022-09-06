import os

import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.photoshop import api as photoshop


class ExtractImage(pyblish.api.ContextPlugin):
    """Save scene before extraction."""

    order = publish.Extractor.order - 0.48
    label = "Extract Image"
    hosts = ["photoshop"]

    families = ["image", "background"]
    formats = ["png", "jpg"]

    def process(self, context):
        stub = photoshop.stub()
        hidden_layer_ids = set()

        all_layers = stub.get_layers()
        for layer in all_layers:
            if not layer.visible:
                hidden_layer_ids.add(layer.id)
        stub.hide_all_others_layers_ids([], layers=all_layers)

        with photoshop.maintained_selection():
            # self.log.info("Extracting %s" % str(list(instance)))
            with photoshop.maintained_visibility(layers=all_layers):
                for instance in context:
                    if instance.data["family"] not in self.families:
                        continue

                    staging_dir = self.staging_dir(instance)
                    self.log.info("Outputting image to {}".format(staging_dir))

                    # Perform extraction
                    files = {}
                    ids = set()
                    layer = instance.data.get("layer")
                    if layer:
                        ids.add(layer.id)
                    add_ids = instance.data.pop("ids", None)
                    if add_ids:
                        ids.update(set(add_ids))
                    extract_ids = set([ll.id for ll in stub.
                                      get_layers_in_layers_ids(ids, all_layers)
                                       if ll.id not in hidden_layer_ids])

                    for extracted_id in extract_ids:
                        stub.set_visible(extracted_id, True)

                    file_basename = os.path.splitext(
                        stub.get_active_document_name()
                    )[0]
                    for extension in self.formats:
                        _filename = "{}.{}".format(file_basename,
                                                   extension)
                        files[extension] = _filename

                        full_filename = os.path.join(staging_dir,
                                                     _filename)
                        stub.saveAs(full_filename, extension, True)
                        self.log.info(f"Extracted: {extension}")

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

                    for extracted_id in extract_ids:
                        stub.set_visible(extracted_id, False)

    def staging_dir(self, instance):
        """Provide a temporary directory in which to store extracted files

        Upon calling this method the staging directory is stored inside
        the instance.data['stagingDir']
        """

        from openpype.pipeline.publish import get_instance_staging_dir

        return get_instance_staging_dir(instance)
