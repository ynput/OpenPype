import os
import logging
import sys
import copy
import clique
import six

from bson.objectid import ObjectId
from pymongo import DeleteMany, ReplaceOne, InsertOne, UpdateOne
import pyblish.api

from openpype.client import (
    get_representations,
    get_subset_by_name,
    get_version_by_name,
)
from openype.lib import source_hash
from openpype.lib.profiles_filtering import filter_profiles
from openpype.lib.file_transaction import FileTransaction
from openpype.pipeline import legacy_io
from openpype.pipeline.publish import KnownPublishError

log = logging.getLogger(__name__)


def assemble(files):
    """Convenience `clique.assemble` wrapper for files of a single collection.

    Unlike `clique.assemble` this wrapper does not allow more than a single
    Collection nor any remainder files. Errors will be raised when not only
    a single collection is assembled.

    Returns:
        clique.Collection: A single sequence Collection

    Raises:
        ValueError: Error is raised when files do not result in a single
                    collected Collection.

    """
    # todo: move this to lib?
    # Get the sequence as a collection. The files must be of a single
    # sequence and have no remainder outside of the collections.
    patterns = [clique.PATTERNS["frames"]]
    collections, remainder = clique.assemble(files,
                                             minimum_items=1,
                                             patterns=patterns)
    if not collections:
        raise ValueError("No collections found in files: "
                         "{}".format(files))
    if remainder:
        raise ValueError("Files found not detected as part"
                         " of a sequence: {}".format(remainder))
    if len(collections) > 1:
        raise ValueError("Files in sequence are not part of a"
                         " single sequence collection: "
                         "{}".format(collections))
    return collections[0]


def get_instance_families(instance):
    """Get all families of the instance"""
    # todo: move this to lib?
    family = instance.data.get("family")
    families = []
    if family:
        families.append(family)

    for _family in (instance.data.get("families") or []):
        if _family not in families:
            families.append(_family)

    return families


def get_frame_padded(frame, padding):
    """Return frame number as string with `padding` amount of padded zeros"""
    return "{frame:0{padding}d}".format(padding=padding, frame=frame)


class IntegrateAsset(pyblish.api.InstancePlugin):
    """Register publish in the database and transfer files to destinations.

    Steps:
        1) Register the subset and version
        2) Transfer the representation files to the destination
        3) Register the representation

    Requires:
        instance.data['representations'] - must be a list and each member
        must be a dictionary with following data:
            'files': list of filenames for sequence, string for single file.
                     Only the filename is allowed, without the folder path.
            'stagingDir': "path/to/folder/with/files"
            'name': representation name (usually the same as extension)
            'ext': file extension
        optional data
            "frameStart"
            "frameEnd"
            'fps'
            "data": additional metadata for each representation.
    """

    label = "Integrate Asset"
    order = pyblish.api.IntegratorOrder
    families = ["workfile",
                "pointcache",
                "camera",
                "animation",
                "model",
                "mayaAscii",
                "mayaScene",
                "setdress",
                "layout",
                "ass",
                "vdbcache",
                "scene",
                "vrayproxy",
                "vrayscene_layer",
                "render",
                "prerender",
                "imagesequence",
                "review",
                "rendersetup",
                "rig",
                "plate",
                "look",
                "audio",
                "yetiRig",
                "yeticache",
                "nukenodes",
                "gizmo",
                "source",
                "matchmove",
                "image",
                "assembly",
                "fbx",
                "textures",
                "action",
                "harmony.template",
                "harmony.palette",
                "editorial",
                "background",
                "camerarig",
                "redshiftproxy",
                "effect",
                "xgen",
                "hda",
                "usd",
                "staticMesh",
                "skeletalMesh",
                "mvLook",
                "mvUsd",
                "mvUsdComposition",
                "mvUsdOverride",
                "simpleUnrealTexture"
                ]

    default_template_name = "publish"

    # Representation context keys that should always be written to
    # the database even if not used by the destination template
    db_representation_context_keys = [
        "project", "asset", "task", "subset", "version", "representation",
        "family", "hierarchy", "username", "output"
    ]
    skip_host_families = []

    def process(self, instance):
        if self._temp_skip_instance_by_settings(instance):
            return

        # Mark instance as processed for legacy integrator
        instance.data["processedWithNewIntegrator"] = True

        # Instance should be integrated on a farm
        if instance.data.get("farm"):
            self.log.info(
                "Instance is marked to be processed on farm. Skipping")
            return

        filtered_repres = self.filter_representations(instance)
        # Skip instance if there are not representations to integrate
        #   all representations should not be integrated
        if not filtered_repres:
            self.log.warning((
                "Skipping, there are no representations"
                " to integrate for instance {}"
            ).format(instance.data["family"]))
            return

        file_transactions = FileTransaction(log=self.log)
        try:
            self.register(instance, file_transactions, filtered_repres)
        except Exception:
            # clean destination
            # todo: preferably we'd also rollback *any* changes to the database
            file_transactions.rollback()
            self.log.critical("Error when registering", exc_info=True)
            six.reraise(*sys.exc_info())

        # Finalizing can't rollback safely so no use for moving it to
        # the try, except.
        file_transactions.finalize()

    def _temp_skip_instance_by_settings(self, instance):
        """Decide if instance will be processed with new or legacy integrator.

        This is temporary solution until we test all usecases with new (this)
        integrator plugin.
        """

        host_name = instance.context.data["hostName"]
        instance_family = instance.data["family"]
        instance_families = set(instance.data.get("families") or [])

        skip = False
        for item in self.skip_host_families:
            if host_name not in item["host"]:
                continue

            families = set(item["families"])
            if instance_family in families:
                skip = True
                break

            for family in instance_families:
                if family in families:
                    skip = True
                    break

            if skip:
                break

        if skip:
            self.log.debug("Instance is marked to be skipped by settings.")
        return skip

    def filter_representations(self, instance):
        # Prepare repsentations that should be integrated
        repres = instance.data.get("representations")
        # Raise error if instance don't have any representations
        if not repres:
            raise KnownPublishError(
                "Instance {} has no representations to integrate".format(
                    instance.data["family"]
                )
            )

        # Validate type of stored representations
        if not isinstance(repres, (list, tuple)):
            raise TypeError(
                "Instance 'files' must be a list, got: {0} {1}".format(
                    str(type(repres)), str(repres)
                )
            )

        # Filter representations
        filtered_repres = []
        for repre in repres:
            if "delete" in repre.get("tags", []):
                continue
            filtered_repres.append(repre)

        return filtered_repres

    def register(self, instance, file_transactions, filtered_repres):
        project_name = legacy_io.active_project()

        instance_stagingdir = instance.data.get("stagingDir")
        if not instance_stagingdir:
            self.log.info((
                "{0} is missing reference to staging directory."
                " Will try to get it from representation."
            ).format(instance))

        else:
            self.log.debug(
                "Establishing staging directory "
                "@ {0}".format(instance_stagingdir)
            )

        template_name = self.get_template_name(instance)

        subset, subset_writes = self.prepare_subset(instance, project_name)
        version, version_writes = self.prepare_version(
            instance, subset, project_name
        )
        instance.data["versionEntity"] = version

        # Get existing representations (if any)
        existing_repres_by_name = {
            repre_doc["name"].lower(): repre_doc
            for repre_doc in get_representations(
                project_name,
                version_ids=[version["_id"]],
                fields=["_id", "name"]
            )
        }

        # Prepare all representations
        prepared_representations = []
        for repre in filtered_repres:
            # todo: reduce/simplify what is returned from this function
            prepared = self.prepare_representation(
                repre,
                template_name,
                existing_repres_by_name,
                version,
                instance_stagingdir,
                instance)

            for src, dst in prepared["transfers"]:
                # todo: add support for hardlink transfers
                file_transactions.add(src, dst)

            prepared_representations.append(prepared)

        # Each instance can also have pre-defined transfers not explicitly
        # part of a representation - like texture resources used by a
        # .ma representation. Those destination paths are pre-defined, etc.
        # todo: should we move or simplify this logic?
        resource_destinations = set()
        for src, dst in instance.data.get("transfers", []):
            file_transactions.add(src, dst, mode=FileTransaction.MODE_COPY)
            resource_destinations.add(os.path.abspath(dst))

        for src, dst in instance.data.get("hardlinks", []):
            file_transactions.add(src, dst, mode=FileTransaction.MODE_HARDLINK)
            resource_destinations.add(os.path.abspath(dst))

        # Bulk write to the database
        # We write the subset and version to the database before the File
        # Transaction to reduce the chances of another publish trying to
        # publish to the same version number since that chance can greatly
        # increase if the file transaction takes a long time.
        legacy_io.bulk_write(subset_writes + version_writes)
        self.log.info("Subset {subset[name]} and Version {version[name]} "
                      "written to database..".format(subset=subset,
                                                     version=version))

        # Process all file transfers of all integrations now
        self.log.debug("Integrating source files to destination ...")
        file_transactions.process()
        self.log.debug(
            "Backed up existing files: {}".format(file_transactions.backups))
        self.log.debug(
            "Transferred files: {}".format(file_transactions.transferred))
        self.log.debug("Retrieving Representation Site Sync information ...")

        # Get the accessible sites for Site Sync
        modules_by_name = instance.context.data["openPypeModules"]
        sync_server_module = modules_by_name["sync_server"]
        sites = sync_server_module.compute_resource_sync_sites(
            project_name=instance.data["projectEntity"]["name"]
        )
        self.log.debug("Sync Server Sites: {}".format(sites))

        # Compute the resource file infos once (files belonging to the
        # version instance instead of an individual representation) so
        # we can re-use those file infos per representation
        anatomy = instance.context.data["anatomy"]
        resource_file_infos = self.get_files_info(resource_destinations,
                                                  sites=sites,
                                                  anatomy=anatomy)

        # Finalize the representations now the published files are integrated
        # Get 'files' info for representations and its attached resources
        representation_writes = []
        new_repre_names_low = set()
        for prepared in prepared_representations:
            representation = prepared["representation"]
            transfers = prepared["transfers"]
            destinations = [dst for src, dst in transfers]
            representation["files"] = self.get_files_info(
                destinations, sites=sites, anatomy=anatomy
            )

            # Add the version resource file infos to each representation
            representation["files"] += resource_file_infos

            # Set up representation for writing to the database. Since
            # we *might* be overwriting an existing entry if the version
            # already existed we'll use ReplaceOnce with `upsert=True`
            representation_writes.append(ReplaceOne(
                filter={"_id": representation["_id"]},
                replacement=representation,
                upsert=True
            ))

            new_repre_names_low.add(representation["name"].lower())

        # Delete any existing representations that didn't get any new data
        # if the instance is not set to append mode
        if not instance.data.get("append", False):
            delete_names = set()
            for name, existing_repres in existing_repres_by_name.items():
                if name not in new_repre_names_low:
                    # We add the exact representation name because `name` is
                    # lowercase for name matching only and not in the database
                    delete_names.add(existing_repres["name"])
            if delete_names:
                representation_writes.append(DeleteMany(
                    filter={
                        "parent": version["_id"],
                        "name": {"$in": list(delete_names)}
                    }
                ))

        # Write representations to the database
        legacy_io.bulk_write(representation_writes)

        # Backwards compatibility
        # todo: can we avoid the need to store this?
        instance.data["published_representations"] = {
            p["representation"]["_id"]: p for p in prepared_representations
        }

        self.log.info("Registered {} representations"
                      "".format(len(prepared_representations)))

    def prepare_subset(self, instance, project_name):
        asset_doc = instance.data.get("assetEntity")
        subset_name = instance.data["subset"]
        self.log.debug("Subset: {}".format(subset_name))

        # Get existing subset if it exists
        subset_doc = get_subset_by_name(
            project_name, subset_name, asset_doc["_id"]
        )

        # Define subset data
        data = {
            "families": get_instance_families(instance)
        }

        subset_group = instance.data.get("subsetGroup")
        if subset_group:
            data["subsetGroup"] = subset_group

        bulk_writes = []
        if subset_doc is None:
            # Create a new subset
            self.log.info("Subset '%s' not found, creating ..." % subset_name)
            subset_doc = {
                "_id": ObjectId(),
                "schema": "openpype:subset-3.0",
                "type": "subset",
                "name": subset_name,
                "data": data,
                "parent": asset_doc["_id"]
            }
            bulk_writes.append(InsertOne(subset_doc))

        else:
            # Update existing subset data with new data and set in database.
            # We also change the found subset in-place so we don't need to
            # re-query the subset afterwards
            subset_doc["data"].update(data)
            bulk_writes.append(UpdateOne(
                {"type": "subset", "_id": subset_doc["_id"]},
                {"$set": {
                    "data": subset_doc["data"]
                }}
            ))

        self.log.info("Prepared subset: {}".format(subset_name))
        return subset_doc, bulk_writes

    def prepare_version(self, instance, subset_doc, project_name):
        version_number = instance.data["version"]

        version_doc = {
            "schema": "openpype:version-3.0",
            "type": "version",
            "parent": subset_doc["_id"],
            "name": version_number,
            "data": self.create_version_data(instance)
        }

        existing_version = get_version_by_name(
            project_name,
            version_number,
            subset_doc["_id"],
            fields=["_id"]
        )

        if existing_version:
            self.log.debug("Updating existing version ...")
            version_doc["_id"] = existing_version["_id"]
        else:
            self.log.debug("Creating new version ...")
            version_doc["_id"] = ObjectId()

        bulk_writes = [ReplaceOne(
            filter={"_id": version_doc["_id"]},
            replacement=version_doc,
            upsert=True
        )]

        self.log.info("Prepared version: v{0:03d}".format(version_doc["name"]))

        return version_doc, bulk_writes

    def prepare_representation(self, repre,
                               template_name,
                               existing_repres_by_name,
                               version,
                               instance_stagingdir,
                               instance):

        # pre-flight validations
        if repre["ext"].startswith("."):
            raise KnownPublishError((
                "Extension must not start with a dot '.': {}"
            ).format(repre["ext"]))

        if repre.get("transfers"):
            raise KnownPublishError((
                "Representation is not allowed to have transfers"
                "data before integration. They are computed in "
                "the integrator. Got: {}"
            ).format(repre["transfers"]))

        # create template data for Anatomy
        template_data = copy.deepcopy(instance.data["anatomyData"])

        # required representation keys
        files = repre['files']
        template_data["representation"] = repre["name"]
        template_data["ext"] = repre["ext"]

        # optionals
        # retrieve additional anatomy data from representation if exists
        for key, anatomy_key in {
            # Representation Key: Anatomy data key
            "resolutionWidth": "resolution_width",
            "resolutionHeight": "resolution_height",
            "fps": "fps",
            "outputName": "output",
            "originalBasename": "originalBasename"
        }.items():
            # Allow to take value from representation
            # if not found also consider instance.data
            value = repre.get(key)
            if value is None:
                value = instance.data.get(key)

            if value is not None:
                template_data[anatomy_key] = value

        stagingdir = repre.get("stagingDir")
        if not stagingdir:
            # Fall back to instance staging dir if not explicitly
            # set for representation in the instance
            self.log.debug((
                "Representation uses instance staging dir: {}"
            ).format(instance_stagingdir))
            stagingdir = instance_stagingdir

        if not stagingdir:
            raise KnownPublishError(
                "No staging directory set for representation: {}".format(repre)
            )

        self.log.debug("Anatomy template name: {}".format(template_name))
        anatomy = instance.context.data['anatomy']
        publish_template_category = anatomy.templates[template_name]
        template = os.path.normpath(publish_template_category["path"])

        is_udim = bool(repre.get("udim"))
        is_sequence_representation = isinstance(files, (list, tuple))
        if is_sequence_representation:
            # Collection of files (sequence)
            if any(os.path.isabs(fname) for fname in files):
                raise KnownPublishError("Given file names contain full paths")

            src_collection = assemble(files)

            destination_indexes = list(src_collection.indexes)
            # Use last frame for minimum padding
            #   - that should cover both 'udim' and 'frame' minimum padding
            destination_padding = len(str(destination_indexes[-1]))
            if not is_udim:
                # Change padding for frames if template has defined higher
                #   padding.
                template_padding = int(
                    publish_template_category["frame_padding"]
                )
                if template_padding > destination_padding:
                    destination_padding = template_padding

                # If the representation has `frameStart` set it renumbers the
                # frame indices of the published collection. It will start from
                # that `frameStart` index instead. Thus if that frame start
                # differs from the collection we want to shift the destination
                # frame indices from the source collection.
                repre_frame_start = repre.get("frameStart")
                if repre_frame_start is not None:
                    index_frame_start = int(repre["frameStart"])
                    # Shift destination sequence to the start frame
                    destination_indexes = [
                        index_frame_start + idx
                        for idx in range(len(destination_indexes))
                    ]

            # To construct the destination template with anatomy we require
            # a Frame or UDIM tile set for the template data. We use the first
            # index of the destination for that because that could've shifted
            # from the source indexes, etc.
            first_index_padded = get_frame_padded(frame=destination_indexes[0],
                                                  padding=destination_padding)
            if is_udim:
                # UDIM representations handle ranges in a different manner
                template_data["udim"] = first_index_padded
            else:
                template_data["frame"] = first_index_padded

            # Construct destination collection from template
            anatomy_filled = anatomy.format(template_data)
            template_filled = anatomy_filled[template_name]["path"]
            repre_context = template_filled.used_values
            self.log.debug("Template filled: {}".format(str(template_filled)))
            dst_collection = assemble([os.path.normpath(template_filled)])

            # Update the destination indexes and padding
            dst_collection.indexes.clear()
            dst_collection.indexes.update(set(destination_indexes))
            dst_collection.padding = destination_padding
            if len(src_collection.indexes) != len(dst_collection.indexes):
                raise KnownPublishError((
                    "This is a bug. Source sequence frames length"
                    " does not match integration frames length"
                ))

            # Multiple file transfers
            transfers = []
            for src_file_name, dst in zip(src_collection, dst_collection):
                src = os.path.join(stagingdir, src_file_name)
                transfers.append((src, dst))

        else:
            # Single file
            fname = files
            if os.path.isabs(fname):
                self.log.error(
                    "Filename in representation is filepath {}".format(fname)
                )
                raise KnownPublishError(
                    "This is a bug. Representation file name is full path"
                )

            # Manage anatomy template data
            template_data.pop("frame", None)
            if is_udim:
                template_data["udim"] = repre["udim"][0]

            # Construct destination filepath from template
            anatomy_filled = anatomy.format(template_data)
            template_filled = anatomy_filled[template_name]["path"]
            repre_context = template_filled.used_values
            dst = os.path.normpath(template_filled)

            # Single file transfer
            src = os.path.join(stagingdir, fname)
            transfers = [(src, dst)]

        # todo: Are we sure the assumption each representation
        #       ends up in the same folder is valid?
        if not instance.data.get("publishDir"):
            instance.data["publishDir"] = (
                anatomy_filled
                [template_name]
                ["folder"]
            )

        for key in self.db_representation_context_keys:
            # Also add these values to the context even if not used by the
            # destination template
            value = template_data.get(key)
            if value is not None:
                repre_context[key] = value

        # Explicitly store the full list even though template data might
        # have a different value because it uses just a single udim tile
        if repre.get("udim"):
            repre_context["udim"] = repre.get("udim")  # store list

        # Use previous representation's id if there is a name match
        existing = existing_repres_by_name.get(repre["name"].lower())
        if existing:
            repre_id = existing["_id"]
        else:
            repre_id = ObjectId()

        # Store first transferred destination as published path data
        # - used primarily for reviews that are integrated to custom modules
        # TODO we should probably store all integrated files
        #   related to the representation?
        published_path = transfers[0][1]
        repre["published_path"] = published_path

        # todo: `repre` is not the actual `representation` entity
        #       we should simplify/clarify difference between data above
        #       and the actual representation entity for the database
        data = repre.get("data", {})
        data.update({'path': published_path, 'template': template})
        representation = {
            "_id": repre_id,
            "schema": "openpype:representation-2.0",
            "type": "representation",
            "parent": version["_id"],
            "name": repre['name'],
            "data": data,

            # Imprint shortcut to context for performance reasons.
            "context": repre_context
        }

        if is_sequence_representation and repre.get("frameStart") is not None:
            representation['context']['frame'] = template_data["frame"]

        return {
            "representation": representation,
            "anatomy_data": template_data,
            "transfers": transfers,
            # todo: avoid the need for 'published_files' used by Integrate Hero
            # backwards compatibility
            "published_files": [transfer[1] for transfer in transfers]
        }

    def create_version_data(self, instance):
        """Create the data dictionary for the version

        Args:
            instance: the current instance being published

        Returns:
            dict: the required information for version["data"]
        """

        context = instance.context

        # create relative source path for DB
        if "source" in instance.data:
            source = instance.data["source"]
        else:
            source = context.data["currentFile"]
            anatomy = instance.context.data["anatomy"]
            source = self.get_rootless_path(anatomy, source)
        self.log.debug("Source: {}".format(source))

        version_data = {
            "families": get_instance_families(instance),
            "time": context.data["time"],
            "author": context.data["user"],
            "source": source,
            "comment": context.data.get("comment"),
            "machine": context.data.get("machine"),
            "fps": instance.data.get("fps", context.data.get("fps"))
        }

        # todo: preferably we wouldn't need this "if dict" etc. logic and
        #       instead be able to rely what the input value is if it's set.
        intent_value = context.data.get("intent")
        if intent_value and isinstance(intent_value, dict):
            intent_value = intent_value.get("value")

        if intent_value:
            version_data["intent"] = intent_value

        # Include optional data if present in
        optionals = [
            "frameStart", "frameEnd", "step", "handles",
            "handleEnd", "handleStart", "sourceHashes"
        ]
        for key in optionals:
            if key in instance.data:
                version_data[key] = instance.data[key]

        # Include instance.data[versionData] directly
        version_data_instance = instance.data.get('versionData')
        if version_data_instance:
            version_data.update(version_data_instance)

        return version_data

    def get_template_name(self, instance):
        """Return anatomy template name to use for integration"""
        # Define publish template name from profiles
        filter_criteria = self.get_profile_filter_criteria(instance)
        template_name_profiles = self._get_template_name_profiles(instance)
        profile = filter_profiles(
            template_name_profiles,
            filter_criteria,
            logger=self.log
        )

        if profile:
            return profile["template_name"]
        return self.default_template_name

    def _get_template_name_profiles(self, instance):
        """Receive profiles for publish template keys.

        Reuse template name profiles from legacy integrator. Goal is to move
        the profile settings out of plugin settings but until that happens we
        want to be able set it at one place and don't break backwards
        compatibility (more then once).
        """

        return (
            instance.context.data["project_settings"]
            ["global"]
            ["publish"]
            ["IntegrateAssetNew"]
            ["template_name_profiles"]
        )

    def get_profile_filter_criteria(self, instance):
        """Return filter criteria for `filter_profiles`"""

        # Anatomy data is pre-filled by Collectors
        anatomy_data = instance.data["anatomyData"]

        # Task can be optional in anatomy data
        task = anatomy_data.get("task", {})

        # Return filter criteria
        return {
            "families": anatomy_data["family"],
            "tasks": task.get("name"),
            "task_types": task.get("type"),
            "hosts": instance.context.data["hostName"],
        }

    def get_rootless_path(self, anatomy, path):
        """Returns, if possible, path without absolute portion from root
            (eg. 'c:\' or '/opt/..')

         This information is platform dependent and shouldn't be captured.
         Example:
             'c:/projects/MyProject1/Assets/publish...' >
             '{root}/MyProject1/Assets...'

        Args:
            anatomy: anatomy part from instance
            path: path (absolute)
        Returns:
            path: modified path if possible, or unmodified path
            + warning logged
        """

        success, rootless_path = anatomy.find_root_template_from_path(path)
        if success:
            path = rootless_path
        else:
            self.log.warning((
                "Could not find root path for remapping \"{}\"."
                " This may cause issues on farm."
            ).format(path))
        return path

    def get_files_info(self, destinations, sites, anatomy):
        """Prepare 'files' info portion for representations.

        Arguments:
            destinations (list): List of transferred file destinations
            sites (list): array of published locations
            anatomy: anatomy part from instance
        Returns:
            output_resources: array of dictionaries to be added to 'files' key
            in representation
        """

        file_infos = []
        for file_path in destinations:
            file_info = self.prepare_file_info(file_path, anatomy, sites=sites)
            file_infos.append(file_info)
        return file_infos

    def prepare_file_info(self, path, anatomy, sites):
        """ Prepare information for one file (asset or resource)

        Arguments:
            path: destination url of published file
            anatomy: anatomy part from instance
            sites: array of published locations,
                [ {'name':'studio', 'created_dt':date} by default
                keys expected ['studio', 'site1', 'gdrive1']

        Returns:
            dict: file info dictionary
        """

        return {
            "_id": ObjectId(),
            "path": self.get_rootless_path(anatomy, path),
            "size": os.path.getsize(path),
            "hash": source_hash(path),
            "sites": sites
        }
