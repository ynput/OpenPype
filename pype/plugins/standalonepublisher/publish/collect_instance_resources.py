import os
import tempfile
import pyblish.api
from copy import deepcopy
import clique


class CollectInstanceResources(pyblish.api.InstancePlugin):
    """Collect instance's resources"""

    # must be after `CollectInstances`
    order = pyblish.api.CollectorOrder + 0.011
    label = "Collect Instance Resources"
    hosts = ["standalonepublisher"]
    families = ["clip"]

    def process(self, instance):
        context = instance.context
        self.log.info(f"Processing instance: {instance}")
        subset_files = dict()
        subset_dirs = list()
        anatomy = instance.context.data["anatomy"]
        anatomy_data = deepcopy(instance.context.data["anatomyData"])
        anatomy_data.update({"root": anatomy.roots})

        subset = instance.data["subset"]
        clip_name = instance.data["clipName"]

        editorial_source_root = instance.data["editorialSourceRoot"]
        editorial_source_path = instance.data["editorialSourcePath"]

        # if `editorial_source_path` then loop trough
        if editorial_source_path:
            # add family if mov or mp4 found which is longer for
            # cutting `trimming` to enable `ExtractTrimmingVideoAudio` plugin
            staging_dir = os.path.normpath(
                tempfile.mkdtemp(prefix="pyblish_tmp_")
            )
            instance.data["stagingDir"] = staging_dir
            instance.data["families"] += ["trimming"]
            return

        # if template patern in path then fill it with `anatomy_data`
        if "{" in editorial_source_root:
            editorial_source_root = editorial_source_root.format(
                **anatomy_data)

        self.log.debug(f"root: {editorial_source_root}")
        # loop `editorial_source_root` and find clip name in folders
        # and look for any subset name alternatives
        for root, dirs, files in os.walk(editorial_source_root):
            correct_clip_dir = None
            for d in dirs:
                # avoid all non clip dirs
                if d not in clip_name:
                    continue
                # found correct dir for clip
                correct_clip_dir = d

            # continue if clip dir was not found
            if not correct_clip_dir:
                continue

            clip_dir_path = os.path.join(root, correct_clip_dir)
            subset_files_items = list()
            # list content of clip dir and search for subset items
            for subset_item in os.listdir(clip_dir_path):
                # avoid all items which are not defined as subsets by name
                if subset not in subset_item:
                    continue

                subset_item_path = os.path.join(
                    clip_dir_path, subset_item)
                # if it is dir store it to `subset_dirs` list
                if os.path.isdir(subset_item_path):
                    subset_dirs.append(subset_item_path)

                # if it is file then store it to `subset_files` list
                if os.path.isfile(subset_item_path):
                    subset_files_items.append(subset_item_path)

            if subset_files_items:
                subset_files.update({clip_dir_path: subset_files_items})
            if correct_clip_dir:
                break

        if subset_dirs:
            # look all dirs and check for subset name alternatives
            copy_instance_data = deepcopy(
                {_k: _v for _k, _v in instance.data.items()})

            # find next available precise subset name with comprahantion
            subset_dir_found = next(
                (d for d in subset_dirs
                 if os.path.basename(d) in subset),
                None)

            if not subset_dir_found:
                instance.data["remove"] = True

            for _dir in subset_dirs:
                sub_dir = os.path.basename(_dir)
                instance_data = instance.data
                # if subset name is only alternative then create new instance
                if sub_dir != subset:
                    new_instance_data = dict()
                    for _key, _value in copy_instance_data.items():
                        new_instance_data[_key] = _value
                        if not isinstance(_value, str):
                            continue
                        if subset in _value:
                            new_instance_data[_key] = _value.replace(
                                subset, sub_dir)
                    new_instance = context.create_instance(
                        new_instance_data["name"])
                    new_instance.data.update(new_instance_data)
                    self.log.info(f"Creating new instance: {new_instance}")
                    instance_data = new_instance.data

                staging_dir = _dir
                files = os.listdir(_dir)
                collections, remainder = clique.assemble(files)
                # self.log.debug(f"collections: {collections}")
                # self.log.debug(f"remainder: {remainder}")
                # self.log.debug(f"staging_dir: {staging_dir}")

                # add staging_dir to instance_data
                instance_data["stagingDir"] = staging_dir
                # add representations to instance_data
                instance_data["representations"] = list()

                # loop trough collections and create representations
                for _collection in collections:
                    ext = _collection.tail
                    repre_data = {
                        "name": ext[1:],
                        "ext": ext[1:],
                        "files": [item for item in _collection],
                        "stagingDir": staging_dir
                    }
                    instance_data["representations"].append(repre_data)

                # loop trough reminders and create representations
                for _reminding_file in remainder:
                    ext = os.path.splitext(_reminding_file)[-1]
                    if ext not in instance_data["extensions"]:
                        continue

                    repre_data = {
                        "name": ext[1:],
                        "ext": ext[1:],
                        "files": _reminding_file,
                        "stagingDir": staging_dir
                    }

                    # exception for thumbnail
                    if "thumb" in _reminding_file:
                        repre_data.update({
                            'name': "thumbnail",
                            'thumbnail': True
                        })

                    # exception for mp4 preview
                    if ".mp4" in _reminding_file:
                        frame_start = instance_data["frameStart"]
                        frame_end = instance_data["frameEnd"]
                        instance_data["families"].append("review")
                        repre_data.update({
                            "frameStart": 0,
                            "frameEnd": (frame_end - frame_start) + 1,
                            "frameStartFtrack": 0,
                            "frameEndFtrack": (frame_end - frame_start) + 1,
                            "step": 1,
                            "fps": context.data.get("fps"),
                            "name": "review",
                            "tags": ["review", "ftrackreview"],
                        })

                    instance_data["representations"].append(repre_data)

                representations = instance_data["representations"]
                self.log.debug(f">>>_<<< representations: {representations}")

        if subset_files:
            staging_dir = list(subset_files.keys()).pop()
            collections, remainder = clique.assemble(subset_files[staging_dir])
            # self.log.debug(f"collections: {collections}")
            # self.log.debug(f"remainder: {remainder}")
            # self.log.debug(f"staging_dir: {staging_dir}")

        # if image sequence then create representation > match
        # with subset name in dict

        # idenfify as image sequence `isSequence` on instance data
