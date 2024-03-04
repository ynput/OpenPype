import os
from pathlib import Path

import unreal

from openpype.pipeline import get_current_project_name
from openpype.pipeline import Anatomy
from openpype.hosts.unreal.api import pipeline
import pyblish.api


class CollectRenderInstances(pyblish.api.InstancePlugin):
    """ This collector will try to find all the rendered frames.

    """
    order = pyblish.api.CollectorOrder
    hosts = ["unreal"]
    families = ["render"]
    label = "Collect Render Instances"

    def process(self, instance):
        self.log.debug("Preparing Rendering Instances")

        context = instance.context

        data = instance.data
        data['remove'] = True

        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        sequence = ar.get_asset_by_object_path(
            data.get('sequence')).get_asset()

        sequences = [{
            "sequence": sequence,
            "output": data.get('output'),
            "frame_range": (
                data.get('frameStart'), data.get('frameEnd'))
        }]

        for s in sequences:
            self.log.debug(f"Processing: {s.get('sequence').get_name()}")
            subscenes = pipeline.get_subsequences(s.get('sequence'))

            if subscenes:
                for ss in subscenes:
                    sequences.append({
                        "sequence": ss.get_sequence(),
                        "output": (f"{s.get('output')}/"
                                   f"{ss.get_sequence().get_name()}"),
                        "frame_range": (
                            ss.get_start_frame(), ss.get_end_frame() - 1)
                    })
            else:
                # Avoid creating instances for camera sequences
                if "_camera" not in s.get('sequence').get_name():
                    seq = s.get('sequence')
                    seq_name = seq.get_name()

                    new_instance = context.create_instance(
                        f"{data.get('subset')}_"
                        f"{seq_name}")
                    new_instance[:] = seq_name

                    new_data = new_instance.data

                    new_data["asset"] = f"/{s.get('output')}"
                    new_data["setMembers"] = seq_name
                    new_data["family"] = "render"
                    new_data["families"] = ["render", "review"]
                    new_data["parent"] = data.get("parent")
                    new_data["subset"] = f"{data.get('subset')}_{seq_name}"
                    new_data["level"] = data.get("level")
                    new_data["output"] = s.get('output')
                    new_data["fps"] = seq.get_display_rate().numerator
                    new_data["frameStart"] = int(s.get('frame_range')[0])
                    new_data["frameEnd"] = int(s.get('frame_range')[1])
                    new_data["sequence"] = seq.get_path_name()
                    new_data["master_sequence"] = data["master_sequence"]
                    new_data["master_level"] = data["master_level"]

                    self.log.debug(f"new instance data: {new_data}")

                    try:
                        project = get_current_project_name()
                        anatomy = Anatomy(project)
                        root = anatomy.roots['renders']
                    except Exception as e:
                        raise Exception((
                            "Could not find render root "
                            "in anatomy settings.")) from e

                    render_dir = f"{root}/{project}/{s.get('output')}"
                    render_path = Path(render_dir)

                    frames = []

                    for x in render_path.iterdir():
                        if x.is_file() and x.suffix == '.png':
                            frames.append(str(x.name))

                    if "representations" not in new_instance.data:
                        new_instance.data["representations"] = []

                    repr = {
                        'frameStart': instance.data["frameStart"],
                        'frameEnd': instance.data["frameEnd"],
                        'name': 'png',
                        'ext': 'png',
                        'files': frames,
                        'stagingDir': render_dir,
                        'tags': ['review']
                    }
                    new_instance.data["representations"].append(repr)
