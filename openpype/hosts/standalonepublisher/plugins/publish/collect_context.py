"""
Requires:
    environment     -> SAPUBLISH_INPATH
    environment     -> SAPUBLISH_OUTPATH

Provides:
    context         -> returnJsonPath (str)
    context         -> project
    context         -> asset
    instance        -> destination_list (list)
    instance        -> representations (list)
    instance        -> source (list)
    instance        -> representations
"""

import os
import json
import copy
from pprint import pformat
import clique
import pyblish.api
from avalon import io


class CollectContextDataSAPublish(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.
    """

    label = "Collect Context - SA Publish"
    order = pyblish.api.CollectorOrder - 0.49
    hosts = ["standalonepublisher"]

    # presets
    batch_extensions = ["edl", "xml", "psd"]

    def process(self, context):
        # get json paths from os and load them
        io.install()

        # get json file context
        input_json_path = os.environ.get("SAPUBLISH_INPATH")

        with open(input_json_path, "r") as f:
            in_data = json.load(f)
        self.log.debug(f"_ in_data: {pformat(in_data)}")

        self.add_files_to_ignore_cleanup(in_data, context)
        # exception for editorial
        if in_data["family"] == "render_mov_batch":
            in_data_list = self.prepare_mov_batch_instances(in_data)

        elif in_data["family"] in ["editorial", "background_batch"]:
            in_data_list = self.multiple_instances(context, in_data)

        else:
            in_data_list = [in_data]

        self.log.debug(f"_ in_data_list: {pformat(in_data_list)}")

        for in_data in in_data_list:
            # create instance
            self.create_instance(context, in_data)

    def add_files_to_ignore_cleanup(self, in_data, context):
        all_filepaths = context.data.get("skipCleanupFilepaths") or []
        for repre in in_data["representations"]:
            files = repre["files"]
            if not isinstance(files, list):
                files = [files]

            dirpath = repre["stagingDir"]
            for filename in files:
                filepath = os.path.normpath(os.path.join(dirpath, filename))
                if filepath not in all_filepaths:
                    all_filepaths.append(filepath)

        context.data["skipCleanupFilepaths"] = all_filepaths

    def multiple_instances(self, context, in_data):
        # avoid subset name duplicity
        if not context.data.get("subsetNamesCheck"):
            context.data["subsetNamesCheck"] = list()

        in_data_list = list()
        representations = in_data.pop("representations")
        for repr in representations:
            in_data_copy = copy.deepcopy(in_data)
            ext = repr["ext"][1:]
            subset = in_data_copy["subset"]
            # filter out non editorial files
            if ext not in self.batch_extensions:
                in_data_copy["representations"] = [repr]
                in_data_copy["subset"] = f"{ext}{subset}"
                in_data_list.append(in_data_copy)

            files = repr.get("files")

            # delete unneeded keys
            delete_repr_keys = ["frameStart", "frameEnd"]
            for k in delete_repr_keys:
                if repr.get(k):
                    repr.pop(k)

            # convert files to list if it isnt
            if not isinstance(files, (tuple, list)):
                files = [files]

            self.log.debug(f"_ files: {files}")
            for index, f in enumerate(files):
                index += 1
                # copy dictionaries
                in_data_copy = copy.deepcopy(in_data_copy)
                repr_new = copy.deepcopy(repr)

                repr_new["files"] = f
                repr_new["name"] = ext
                in_data_copy["representations"] = [repr_new]

                # create subset Name
                new_subset = f"{ext}{index}{subset}"
                while new_subset in context.data["subsetNamesCheck"]:
                    index += 1
                    new_subset = f"{ext}{index}{subset}"

                context.data["subsetNamesCheck"].append(new_subset)
                in_data_copy["subset"] = new_subset
                in_data_list.append(in_data_copy)
                self.log.info(f"Creating subset: {ext}{index}{subset}")

        return in_data_list

    def prepare_mov_batch_instances(self, in_data):
        """Copy of `multiple_instances` method.

        Method was copied because `batch_extensions` is used in
        `multiple_instances` but without any family filtering. Since usage
        of the filtering is unknown and modification of that part may break
        editorial or PSD batch publishing it was decided to create a copy with
        this family specific filtering. Also "frameStart" and "frameEnd" keys
        are removed from instance which is needed for this processing.

        Instance data will also care about families.

        TODO:
        - Merge possible logic with `multiple_instances` method.
        """
        self.log.info("Preparing data for mov batch processing.")
        in_data_list = []

        representations = in_data.pop("representations")
        for repre in representations:
            self.log.debug("Processing representation with files {}".format(
                str(repre["files"])
            ))
            ext = repre["ext"][1:]

            # Rename representation name
            repre_name = repre["name"]
            if repre_name.startswith(ext + "_"):
                repre["name"] = ext
            # Skip files that are not available for mov batch publishing
            # TODO add dynamic expected extensions by family from `in_data`
            #   - with this modification it would be possible to use only
            #     `multiple_instances` method
            expected_exts = ["mov"]
            if ext not in expected_exts:
                self.log.warning((
                    "Skipping representation."
                    " Does not match expected extensions <{}>. {}"
                ).format(", ".join(expected_exts), str(repre)))
                continue

            files = repre["files"]
            # Convert files to list if it isnt
            if not isinstance(files, (tuple, list)):
                files = [files]

            # Loop through files and create new instance per each file
            for filename in files:
                # Create copy of representation and change it's files and name
                new_repre = copy.deepcopy(repre)
                new_repre["files"] = filename
                new_repre["name"] = ext
                new_repre["thumbnail"] = True

                if "tags" not in new_repre:
                    new_repre["tags"] = []
                new_repre["tags"].append("review")

                # Prepare new subset name (temporary name)
                # - subset name will be changed in batch specific plugins
                new_subset_name = "{}{}".format(
                    in_data["subset"],
                    os.path.basename(filename)
                )
                # Create copy of instance data as new instance and pass in new
                #   representation
                in_data_copy = copy.deepcopy(in_data)
                in_data_copy["representations"] = [new_repre]
                in_data_copy["subset"] = new_subset_name
                if "families" not in in_data_copy:
                    in_data_copy["families"] = []
                in_data_copy["families"].append("review")

                in_data_list.append(in_data_copy)

        return in_data_list

    def create_instance(self, context, in_data):
        subset = in_data["subset"]
        # If instance data already contain families then use it
        instance_families = in_data.get("families") or []

        instance = context.create_instance(subset)
        instance.data.update(
            {
                "subset": subset,
                "asset": in_data["asset"],
                "label": subset,
                "name": subset,
                "family": in_data["family"],
                # "version": in_data.get("version", 1),
                "frameStart": in_data.get("representations", [None])[0].get(
                    "frameStart", None
                ),
                "frameEnd": in_data.get("representations", [None])[0].get(
                    "frameEnd", None
                ),
                "families": instance_families
            }
        )
        self.log.info("collected instance: {}".format(pformat(instance.data)))
        self.log.info("parsing data: {}".format(pformat(in_data)))

        instance.data["destination_list"] = list()
        instance.data["representations"] = list()
        instance.data["source"] = "standalone publisher"

        for component in in_data["representations"]:
            component["destination"] = component["files"]
            component["stagingDir"] = component["stagingDir"]

            if isinstance(component["files"], list):
                collections, _remainder = clique.assemble(component["files"])
                self.log.debug("collecting sequence: {}".format(collections))
                instance.data["frameStart"] = int(component["frameStart"])
                instance.data["frameEnd"] = int(component["frameEnd"])
                if component.get("fps"):
                    instance.data["fps"] = int(component["fps"])

            ext = component["ext"]
            if ext.startswith("."):
                component["ext"] = ext[1:]

            if component["preview"]:
                instance.data["families"].append("review")
                component["tags"] = ["review"]
                self.log.debug("Adding review family")

            if "psd" in component["name"]:
                instance.data["source"] = component["files"]
                self.log.debug("Adding image:background_batch family")

            instance.data["representations"].append(component)
