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
    families = ["render.local", "prerender.local", "still.local"]

    def process(self, instance):
        node = instance[0]
        # This should be a ContextPlugin, but this is a workaround
        # for a bug in pyblish to run once for a family: issue #250
        context = instance.context
        key = "__hasRun{}".format(self.__class__.__name__)
        if context.data.get(key, False):
            return
        else:
            context.data[key] = True

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

        if "files" not in instance.data:
            instance.data["files"] = list()

        instance.data["files"] = [os.listdir(temp_dir)]

        self.log.info("Extracted instance '{0}' to: {1}".format(
            instance.name,
            output_dir
        ))

        collections, remainder = clique.assemble(*instance.data['files'])
        self.log.info('collections: {}'.format(str(collections)))

        collection = collections[0]
        instance.data['collection'] = collection

        self.log.info('Finished render')
        return
