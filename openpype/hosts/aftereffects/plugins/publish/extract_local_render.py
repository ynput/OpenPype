import os

from openpype.pipeline import publish
from openpype.hosts.aftereffects.api import get_stub


class ExtractLocalRender(publish.Extractor):
    """Render RenderQueue locally."""

    order = publish.Extractor.order - 0.47
    label = "Extract Local Render"
    hosts = ["aftereffects"]
    families = ["renderLocal", "render.local"]

    def process(self, instance):
        stub = get_stub()
        staging_dir = instance.data["stagingDir"]
        self.log.debug("staging_dir::{}".format(staging_dir))

        file_names = instance.data["file_names"]
        # pull file name collected value from Render Queue Output module
        if not file_names:
            raise ValueError("No file extension set in Render Queue")

        comp_id = instance.data['comp_id']
        stub.render(staging_dir, comp_id)

        representations = []
        encoding = instance.data.get("encoding", None)
        for file_number, file_name in enumerate(file_names):
            _, ext = os.path.splitext(os.path.basename(file_name))
            ext = ext[1:]
            files = []

            for found_file_name in os.listdir(staging_dir):

                self.log.warning(found_file_name)
                self.log.warning(file_name)

                if not found_file_name.endswith(ext):
                    continue

                self.log.info("found_file_name::{}".format(found_file_name))
                files.append(found_file_name)

            if not files:
                self.log.info("no files")
                return

            # single file cannot be wrapped in array
            resulting_files = files
            if len(files) == 1:
                resulting_files = files[0]

            # Check if multiple encoding informations are passed
            if type(instance.data.get("encoding", None)) is list:
                encoding = instance.data["encoding"][file_number]

            repre_data = {
                "frameStart": instance.data["frameStart"],
                "frameEnd": instance.data["frameEnd"],
                "encoding": encoding,
                "name": ext,
                "ext": ext,
                "files": resulting_files,
                "stagingDir": staging_dir
            }
            self.log.warning(repre_data)
            first_repre = not representations
            if instance.data["review"] and first_repre:
                repre_data["tags"] = ["review"]
                thumbnail_path = os.path.join(staging_dir, files[0])
                instance.data["thumbnailSource"] = thumbnail_path

            representations.append(repre_data)

        instance.data["representations"] = representations
