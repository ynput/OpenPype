import os
import shutil

import pyblish.api
import clique
import nuke
from openpype.hosts.nuke import api as napi
from openpype.pipeline import publish
from openpype.lib import collect_frames


class NukeRenderLocal(publish.Extractor,
                      publish.ColormanagedPyblishPluginMixin):
    """Render the current Nuke composition locally.

    Extract the result of savers by starting a comp render
    This will run the local render of Fusion.

    Allows to use last published frames and overwrite only specific ones
    (set in instance.data.get("frames_to_fix"))
    """

    order = pyblish.api.ExtractorOrder
    label = "Render Local"
    hosts = ["nuke"]
    families = ["render.local", "prerender.local", "image.local"]

    def process(self, instance):
        child_nodes = (
            instance.data.get("transientData", {}).get("childNodes")
            or instance
        )

        node = None
        for x in child_nodes:
            if x.Class() == "Write":
                node = x

        self.log.debug("instance collected: {}".format(instance.data))

        node_subset_name = instance.data.get("name", None)

        first_frame = instance.data.get("frameStartHandle", None)
        last_frame = instance.data.get("frameEndHandle", None)

        filenames = []
        node_file = node["file"]
        # Collect expected filepaths for each frame
        # - for cases that output is still image is first created set of
        #   paths which is then sorted and converted to list
        expected_paths = list(sorted({
            node_file.evaluate(frame)
            for frame in range(first_frame, last_frame + 1)
        }))
        # Extract only filenames for representation
        filenames.extend([
            os.path.basename(filepath)
            for filepath in expected_paths
        ])

        # Ensure output directory exists.
        out_dir = os.path.dirname(expected_paths[0])
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        frames_to_render = [(first_frame, last_frame)]

        frames_to_fix = instance.data.get("frames_to_fix")
        if instance.data.get("last_version_published_files") and frames_to_fix:
            frames_to_render = self._get_frames_to_render(frames_to_fix)
            anatomy = instance.context.data["anatomy"]
            self._copy_last_published(anatomy, instance, out_dir,
                                      filenames)

        for render_first_frame, render_last_frame in frames_to_render:

            self.log.info("Starting render")
            self.log.info("Start frame: {}".format(render_first_frame))
            self.log.info("End frame: {}".format(render_last_frame))

            # Render frames
            nuke.execute(
                str(node_subset_name),
                int(render_first_frame),
                int(render_last_frame)
            )

        ext = node["file_type"].value()
        colorspace = napi.get_colorspace_from_node(node)

        if "representations" not in instance.data:
            instance.data["representations"] = []

        if len(filenames) == 1:
            repre = {
                'name': ext,
                'ext': ext,
                'files': filenames[0],
                "stagingDir": out_dir
            }
        else:
            repre = {
                'name': ext,
                'ext': ext,
                'frameStart': (
                    "{{:0>{}}}"
                    .format(len(str(last_frame)))
                    .format(first_frame)
                ),
                'files': filenames,
                "stagingDir": out_dir
            }

        # inject colorspace data
        self.set_representation_colorspace(
            repre, instance.context,
            colorspace=colorspace
        )

        instance.data["representations"].append(repre)

        self.log.debug("Extracted instance '{0}' to: {1}".format(
            instance.name,
            out_dir
        ))

        families = instance.data["families"]
        # redefinition of families
        if "render.local" in families:
            instance.data['family'] = 'render'
            families.remove('render.local')
            families.insert(0, "render2d")
            instance.data["anatomyData"]["family"] = "render"
        elif "prerender.local" in families:
            instance.data['family'] = 'prerender'
            families.remove('prerender.local')
            families.insert(0, "prerender")
            instance.data["anatomyData"]["family"] = "prerender"
        elif "image.local" in families:
            instance.data['family'] = 'image'
            families.remove('image.local')
            instance.data["anatomyData"]["family"] = "image"
        instance.data["families"] = families

        collections, remainder = clique.assemble(filenames)
        self.log.debug('collections: {}'.format(str(collections)))

        if collections:
            collection = collections[0]
            instance.data['collection'] = collection

        self.log.info('Finished render')

        self.log.debug("_ instance.data: {}".format(instance.data))

    def _copy_last_published(self, anatomy, instance, out_dir,
                             expected_filenames):
        """Copies last published files to temporary out_dir.

        These are base of files which will be extended/fixed for specific
        frames.
        Renames published file to expected file name based on frame, eg.
        test_project_test_asset_subset_v005.1001.exr > new_render.1001.exr
        """
        last_published = instance.data["last_version_published_files"]
        last_published_and_frames = collect_frames(last_published)

        expected_and_frames = collect_frames(expected_filenames)
        frames_and_expected = {v: k for k, v in expected_and_frames.items()}
        for file_path, frame in last_published_and_frames.items():
            file_path = anatomy.fill_root(file_path)
            if not os.path.exists(file_path):
                continue
            target_file_name = frames_and_expected.get(frame)
            if not target_file_name:
                continue

            out_path = os.path.join(out_dir, target_file_name)
            self.log.debug("Copying '{}' -> '{}'".format(file_path, out_path))
            shutil.copy(file_path, out_path)

            # TODO shouldn't this be uncommented
            # instance.context.data["cleanupFullPaths"].append(out_path)

    def _get_frames_to_render(self, frames_to_fix):
        """Return list of frame range tuples to render

        Args:
            frames_to_fix (str): specific or range of frames to be rerendered
             (1005, 1009-1010)
        Returns:
            (list): [(1005, 1005), (1009-1010)]
        """
        frames_to_render = []

        for frame_range in frames_to_fix.split(","):
            if frame_range.isdigit():
                render_first_frame = frame_range
                render_last_frame = frame_range
            elif '-' in frame_range:
                frames = frame_range.split('-')
                render_first_frame = int(frames[0])
                render_last_frame = int(frames[1])
            else:
                raise ValueError("Wrong format of frames to fix {}"
                                 .format(frames_to_fix))
            frames_to_render.append((render_first_frame,
                                     render_last_frame))
        return frames_to_render
