import os

import openpype.api
from openpype.hosts.photoshop import api as photoshop


class ExtractImage(openpype.api.Extractor):
    """Produce a flattened image file from instance

    This plug-in takes into account only the layers in the group.
    """

    label = "Extract Image"
    hosts = ["photoshop"]
    families = ["image", "background"]
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
                layer = instance.data.get("layer")
                ids = set([layer.id])
                add_ids = instance.data.pop("ids", None)
                if add_ids:
                    ids.update(set(add_ids))
                extract_ids = set([ll.id for ll in stub.
                                   get_layers_in_layers_ids(ids)])
                stub.hide_all_others_layers_ids(extract_ids)

                file_basename = os.path.splitext(
                    stub.get_active_document_name()
                )[0]
                for extension in self.formats:
                    _filename = "{}.{}".format(file_basename, extension)
                    files[extension] = _filename

                    full_filename = os.path.join(staging_dir, _filename)
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
