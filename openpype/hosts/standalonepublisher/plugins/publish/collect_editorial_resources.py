import os
import re
import tempfile
import pyblish.api
from copy import deepcopy
import clique


class CollectInstanceResources(pyblish.api.InstancePlugin):
    """Collect instance's resources"""

    # must be after `CollectInstances`
    order = pyblish.api.CollectorOrder + 0.011
    label = "Collect Editorial Resources"
    hosts = ["standalonepublisher"]
    families = ["clip"]

    def process(self, instance):
        self.context = instance.context
        self.log.info(f"Processing instance: {instance}")
        self.new_instances = []
        subset_files = dict()
        subset_dirs = list()
        anatomy = self.context.data["anatomy"]
        anatomy_data = deepcopy(self.context.data["anatomyData"])
        anatomy_data.update({"root": anatomy.roots})

        subset = instance.data["subset"]
        clip_name = instance.data["clipName"]

        editorial_source_root = instance.data["editorialSourceRoot"]
        editorial_source_path = instance.data["editorialSourcePath"]

        # if `editorial_source_path` then loop through
        if editorial_source_path:
            # add family if mov or mp4 found which is longer for
            # cutting `trimming` to enable `ExtractTrimmingVideoAudio` plugin
            staging_dir = os.path.normpath(
                tempfile.mkdtemp(prefix="pyblish_tmp_")
            )
            instance.data["stagingDir"] = staging_dir
            instance.data["families"] += ["trimming"]
            return

        # if template pattern in path then fill it with `anatomy_data`
        if "{" in editorial_source_root:
            editorial_source_root = editorial_source_root.format(
                **anatomy_data)

        self.log.debug(f"root: {editorial_source_root}")
        # loop `editorial_source_root` and find clip name in folders
        # and look for any subset name alternatives
        for root, dirs, _files in os.walk(editorial_source_root):
            # search only for directories related to clip name
            correct_clip_dir = None
            for _d_search in dirs:
                # avoid all non clip dirs
                if _d_search not in clip_name:
                    continue
                # found correct dir for clip
                correct_clip_dir = _d_search

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

            # break the loop if correct_clip_dir was captured
            # no need to cary on if correct folder was found
            if correct_clip_dir:
                break

        if subset_dirs:
            # look all dirs and check for subset name alternatives
            for _dir in subset_dirs:
                instance_data = deepcopy(
                    {k: v for k, v in instance.data.items()})
                sub_dir = os.path.basename(_dir)
                # if subset name is only alternative then create new instance
                if sub_dir != subset:
                    instance_data = self.duplicate_instance(
                        instance_data, subset, sub_dir)

                # create all representations
                self.create_representations(
                    os.listdir(_dir), instance_data, _dir)

                if sub_dir == subset:
                    self.new_instances.append(instance_data)
                    # instance.data.update(instance_data)

        if subset_files:
            unique_subset_names = list()
            root_dir = list(subset_files.keys()).pop()
            files_list = subset_files[root_dir]
            search_pattern = f"({subset}[A-Za-z0-9]+)(?=[\\._\\s])"
            for _file in files_list:
                pattern = re.compile(search_pattern)
                match = pattern.findall(_file)
                if not match:
                    continue
                match_subset = match.pop()
                if match_subset in unique_subset_names:
                    continue
                unique_subset_names.append(match_subset)

            self.log.debug(f"unique_subset_names: {unique_subset_names}")

            for _un_subs in unique_subset_names:
                instance_data = self.duplicate_instance(
                    instance.data, subset, _un_subs)

                # create all representations
                self.create_representations(
                    [os.path.basename(f) for f in files_list
                     if _un_subs in f],
                    instance_data, root_dir)

        # remove the original instance as it had been used only
        # as template and is duplicated
        self.context.remove(instance)

        # create all instances in self.new_instances into context
        for new_instance in self.new_instances:
            _new_instance = self.context.create_instance(
                new_instance["name"])
            _new_instance.data.update(new_instance)

    def duplicate_instance(self, instance_data, subset, new_subset):

        new_instance_data = dict()
        for _key, _value in instance_data.items():
            new_instance_data[_key] = _value
            if not isinstance(_value, str):
                continue
            if subset in _value:
                new_instance_data[_key] = _value.replace(
                    subset, new_subset)

        self.log.info(f"Creating new instance: {new_instance_data['name']}")
        self.new_instances.append(new_instance_data)
        return new_instance_data

    def create_representations(
            self, files_list, instance_data, staging_dir):
        """ Create representations from Collection object
        """
        # collecting frames for later frame start/end reset
        frames = list()
        # break down Collection object to collections and reminders
        collections, remainder = clique.assemble(files_list)
        # add staging_dir to instance_data
        instance_data["stagingDir"] = staging_dir
        # add representations to instance_data
        instance_data["representations"] = list()

        collection_head_name = None
        # loop through collections and create representations
        for _collection in collections:
            ext = _collection.tail[1:]
            collection_head_name = _collection.head
            frame_start = list(_collection.indexes)[0]
            frame_end = list(_collection.indexes)[-1]
            repre_data = {
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "name": ext,
                "ext": ext,
                "files": [item for item in _collection],
                "stagingDir": staging_dir
            }

            if instance_data.get("keepSequence"):
                repre_data_keep = deepcopy(repre_data)
                instance_data["representations"].append(repre_data_keep)

            if "review" in instance_data["families"]:
                repre_data.update({
                    "thumbnail": True,
                    "frameStartFtrack": frame_start,
                    "frameEndFtrack": frame_end,
                    "step": 1,
                    "fps": self.context.data.get("fps"),
                    "name": "review",
                    "tags": ["review", "ftrackreview", "delete"],
                })
            instance_data["representations"].append(repre_data)

            # add to frames for frame range reset
            frames.append(frame_start)
            frames.append(frame_end)

        # loop through reminders and create representations
        for _reminding_file in remainder:
            ext = os.path.splitext(_reminding_file)[-1][1:]
            if ext not in instance_data["extensions"]:
                continue
            if collection_head_name and (
                (collection_head_name + ext) not in _reminding_file
            ) and (ext in ["mp4", "mov"]):
                self.log.info(f"Skipping file: {_reminding_file}")
                continue
            frame_start = 1
            frame_end = 1

            repre_data = {
                "name": ext,
                "ext": ext,
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
            if ext in ["mp4", "mov"]:
                frame_start = 0
                frame_end = (
                    (instance_data["frameEnd"] - instance_data["frameStart"])
                    + 1)
                # add review ftrack family into families
                for _family in ["review", "ftrack"]:
                    if _family not in instance_data["families"]:
                        instance_data["families"].append(_family)
                repre_data.update({
                    "frameStart": frame_start,
                    "frameEnd": frame_end,
                    "frameStartFtrack": frame_start,
                    "frameEndFtrack": frame_end,
                    "step": 1,
                    "fps": self.context.data.get("fps"),
                    "name": "review",
                    "thumbnail": True,
                    "tags": ["review", "ftrackreview", "delete"],
                })

            # add to frames for frame range reset only if no collection
            if not collections:
                frames.append(frame_start)
                frames.append(frame_end)

            instance_data["representations"].append(repre_data)

        # reset frame start / end
        instance_data["frameStart"] = min(frames)
        instance_data["frameEnd"] = max(frames)
