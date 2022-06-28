from pathlib import Path

import unreal

import openpype.api


class ExtractRender(openpype.api.Extractor):
    """Extract render."""

    label = "Extract Render"
    hosts = ["unreal"]
    families = ["render"]
    optional = True

    def process(self, instance):
        # Define extract output file path
        stagingdir = self.staging_dir(instance)

        # Perform extraction
        self.log.info("Performing extraction..")

        # Get the render output directory
        project_dir = unreal.Paths.project_dir()
        render_dir = (f"{project_dir}/Saved/MovieRenders/"
                      f"{instance.data['subset']}")

        assert unreal.Paths.directory_exists(render_dir), \
            "Render directory does not exist"

        render_path = Path(render_dir)

        frames = []

        for x in render_path.iterdir():
            if x.is_file() and x.suffix == '.png':
                frames.append(str(x))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        render_representation = {
            'name': 'png',
            'ext': 'png',
            'files': frames,
            "stagingDir": stagingdir,
        }
        instance.data["representations"].append(render_representation)
