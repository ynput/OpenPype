import pyblish.api
import nuke
import os
import pype
import clique


class NukeRenderLocal(pype.api.Extractor):
    # TODO: rewrite docstring to nuke
    """Render the current Fusion composition locally.

    Extract the result of savers by starting a comp render
    This will run the local render of Fusion.

    """

    order = pyblish.api.ExtractorOrder
    label = "Render Local"
    hosts = ["nuke"]
    families = ["render.local"]

    def process(self, instance):
        node = instance[0]
        context = instance.context

        self.log.debug("instance collected: {}".format(instance.data))

        first_frame = instance.data.get("startFrame", None)
        last_frame = instance.data.get("endFrame", None)
        node_subset_name = instance.data.get("name", None)

        # swap path to stageDir
        temp_dir = self.staging_dir(instance).replace("\\", "/")
        output_dir = instance.data.get("outputDir")
        path = node['file'].value()
        node['file'].setValue(path.replace(output_dir, temp_dir))

        self.log.info("Starting render")
        self.log.info("Start frame: {}".format(first_frame))
        self.log.info("End frame: {}".format(last_frame))

        # Render frames
        nuke.execute(
            node_subset_name,
            int(first_frame),
            int(last_frame)
        )

        # swap path back to publish path
        path = node['file'].value()
        node['file'].setValue(path.replace(temp_dir, output_dir))
        ext = node["file_type"].value()

        if "representations" not in instance.data:
            instance.data["representations"] = []

        collected_frames = os.listdir(temp_dir)
        repre = {
            'name': ext,
            'ext': ext,
            'files': collected_frames,
            "stagingDir": temp_dir,
            "anatomy_template": "render"
        }
        instance.data["representations"].append(repre)

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name,
            temp_dir
        ))

        instance.data['families'].append('render')

        collections, remainder = clique.assemble(collected_frames)
        self.log.info('collections: {}'.format(str(collections)))

        if collections:
            collection = collections[0]
            instance.data['collection'] = collection

        self.log.info('Finished render')
        return
