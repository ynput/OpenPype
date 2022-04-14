import os
import logging
import sys
import copy
import clique
import six
from collections import deque, defaultdict

from bson.objectid import ObjectId
from pymongo import DeleteMany, ReplaceOne, InsertOne, UpdateOne
import pyblish.api
from avalon import io
import openpype.api
from datetime import datetime
from openpype.lib.profiles_filtering import filter_profiles
from openpype.lib.file_transaction import FileTransaction

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


def get_first_frame_padded(collection):
    """Return first frame as padded number from `clique.Collection`"""
    start_frame = next(iter(collection.indexes))
    return get_frame_padded(start_frame, padding=collection.padding)


def bulk_write(writes):
    """Convenience function to bulk write into active project database"""
    return io._database[io.Session["AVALON_PROJECT"]].bulk_write(writes)


class IntegrateAssetNew(pyblish.api.InstancePlugin):
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

    label = "Integrate Asset New"
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
                "usdComposition",
                "usdOverride",
                "simpleUnrealTexture"
                ]
    exclude_families = ["clip"]
    default_template_name = "publish"

    # Representation context keys that should always be written to
    # the database even if not used by the destination template
    db_representation_context_keys = [
        "project", "asset", "task", "subset", "version", "representation",
        "family", "hierarchy", "username"
    ]

    # Attributes set by settings
    template_name_profiles = None

    def process(self, instance):

        # Exclude instances that also contain families from exclude families
        families = set(get_instance_families(instance))
        exclude = families & set(self.exclude_families)
        if exclude:
            self.log.debug("Instance not integrated due to exclude "
                           "families found: {}".format(", ".join(exclude)))
            return

        file_transactions = FileTransaction(log=self.log)
        try:
            self.register(instance, file_transactions)
        except Exception:
            # clean destination
            # todo: preferably we'd also rollback *any* changes to the database
            file_transactions.rollback()
            self.log.critical("Error when registering", exc_info=True)
            six.reraise(*sys.exc_info())

        # Finalizing can't rollback safely so no use for moving it to
        # the try, except.
        file_transactions.finalize()

    def register(self, instance, file_transactions):

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

        # Ensure at least one representation is set up for registering.
        repres = instance.data.get("representations")
        assert repres, "Instance has no representations data"
        assert isinstance(repres, (list, tuple)), (
            "Instance 'representations' must be a list, got: {0} {1}".format(
                str(type(repres)), str(repres)
            )
        )

        template_name = self.get_template_name(instance)

        subset, subset_writes = self.prepare_subset(instance)
        version, version_writes = self.prepare_version(instance, subset)
        instance.data["versionEntity"] = version

        # Get existing representations (if any)
        existing_repres_by_name = {
            repres["name"].lower(): repres for repres in io.find(
                {
                    "parent": version["_id"],
                    "type": "representation"
                },
                # Only care about id and name of existing representations
                projection={"_id": True, "name": True}
            )
        }

        # Prepare all representations
        prepared_representations = []
        for repre in instance.data["representations"]:

            if "delete" in repre.get("tags", []):
                self.log.debug("Skipping representation marked for deletion: "
                               "{}".format(repre))
                continue

            # todo: reduce/simplify what is returned from this function
            prepared = self.prepare_representation(repre,
                                                   template_name,
                                                   existing_repres_by_name,
                                                   version,
                                                   instance_stagingdir,
                                                   instance)

            for src, dst in prepared["transfers"]:
                # todo: add support for hardlink transfers
                file_transactions.add(src, dst)

            prepared_representations.append(prepared)

        if not prepared_representations:
            # Even though we check `instance.data["representations"]` earlier
            # this could still happen if all representations were tagged with
            # "delete" and thus are skipped for integration
            raise RuntimeError("No representations prepared to publish.")

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
        bulk_write(subset_writes + version_writes)
        self.log.info("Subset {subset[name]} and Version {version[name]} "
                      "written to database..".format(subset=subset,
                                                     version=version))

        # Process all file transfers of all integrations now
        self.log.debug("Integrating source files to destination ...")
        file_transactions.process()
        self.log.debug("Backed up existing files: "
                       "{}".format(file_transactions.backups))
        self.log.debug("Transferred files: "
                       "{}".format(file_transactions.transferred))
        self.log.debug("Retrieving Representation Site Sync information ...")

        # Get the accessible sites for Site Sync
        sites = SiteSync.compute_resource_sync_sites(
            system_settings=instance.context.data["system_settings"],
            project_settings=instance.context.data["project_settings"]
        )
        self.log.debug("Site Sync Sites: {}".format(sites))

        # Compute the resource file infos once (files belonging to the
        # version instance instead of an individual representation) so
        # we can re-use those file infos per representation
        anatomy = instance.context.data["anatomy"]
        resource_file_infos = self.prepare_file_info(resource_destinations,
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
        bulk_write(representation_writes)

        # Backwards compatibility
        # todo: can we avoid the need to store this?
        instance.data["published_representations"] = {
            p["representation"]["_id"]: p for p in prepared_representations
        }

        self.log.info("Registered {} representations"
                      "".format(len(prepared_representations)))

    def prepare_subset(self, instance):
        asset = instance.data.get("assetEntity")
        subset_name = instance.data["subset"]
        self.log.debug("Subset: {}".format(subset_name))

        # Get existing subset if it exists
        subset = io.find_one({
            "type": "subset",
            "parent": asset["_id"],
            "name": subset_name
        })

        # Define subset data
        data = {
            "families": get_instance_families(instance)
        }

        subset_group = instance.data.get("subsetGroup")
        if subset_group:
            data["subsetGroup"] = subset_group

        bulk_writes = []
        if subset is None:
            # Create a new subset
            self.log.info("Subset '%s' not found, creating ..." % subset_name)
            subset = {
                "_id": ObjectId(),
                "schema": "openpype:subset-3.0",
                "type": "subset",
                "name": subset_name,
                "data": data,
                "parent": asset["_id"]
            }
            bulk_writes.append(InsertOne(subset))

        else:
            # Update existing subset data with new data and set in database.
            # We also change the found subset in-place so we don't need to
            # re-query the subset afterwards
            subset["data"].update(data)
            bulk_writes.append(UpdateOne(
                {"type": "subset", "_id": subset["_id"]},
                {"$set": {
                    "data": subset["data"]
                }}
            ))

        self.log.info("Prepared subset: {}".format(subset_name))
        return subset, bulk_writes

    def prepare_version(self, instance, subset):

        version_number = instance.data["version"]

        version = {
            "schema": "openpype:version-3.0",
            "type": "version",
            "parent": subset["_id"],
            "name": version_number,
            "data": self.create_version_data(instance)
        }

        existing_version = io.find_one({
            'type': 'version',
            'parent': subset["_id"],
            'name': version_number
        }, projection={"_id": True})

        if existing_version:
            self.log.debug("Updating existing version ...")
            version["_id"] = existing_version["_id"]
        else:
            self.log.debug("Creating new version ...")
            version["_id"] = ObjectId()

        bulk_writes = [ReplaceOne(
            filter={"_id": version["_id"]},
            replacement=version,
            upsert=True
        )]

        self.log.info("Prepared version: v{0:03d}".format(version["name"]))

        return version, bulk_writes

    def prepare_representation(self, repre,
                               template_name,
                               existing_repres_by_name,
                               version,
                               instance_stagingdir,
                               instance):

        # pre-flight validations
        if repre["ext"].startswith("."):
            raise ValueError("Extension must not start with a dot '.': "
                             "{}".format(repre["ext"]))

        if repre.get("transfers"):
            raise ValueError("Representation is not allowed to have transfers"
                             "data before integration. They are computed in "
                             "the integrator"
                             "Got: {}".format(repre["transfers"]))

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
            if key in repre:
                value = repre[key]
            elif key in instance.data:
                value = instance.data[key]
            else:
                continue
            template_data[anatomy_key] = value

        if repre.get('stagingDir'):
            stagingdir = repre['stagingDir']
        else:
            # Fall back to instance staging dir if not explicitly
            # set for representation in the instance
            self.log.debug("Representation uses instance staging dir: "
                           "{}".format(instance_stagingdir))
            stagingdir = instance_stagingdir
        if not stagingdir:
            raise ValueError("No staging directory set for representation: "
                             "{}".format(repre))

        self.log.debug("Anatomy template name: {}".format(template_name))
        anatomy = instance.context.data['anatomy']
        template = os.path.normpath(anatomy.templates[template_name]["path"])

        is_udim = bool(repre.get("udim"))
        is_sequence_representation = isinstance(files, (list, tuple))
        if is_sequence_representation:
            # Collection of files (sequence)
            assert not any(os.path.isabs(fname) for fname in files), (
                "Given file names contain full paths"
            )

            src_collection = assemble(files)

            # If the representation has `frameStart` set it renumbers the
            # frame indices of the published collection. It will start from
            # that `frameStart` index instead. Thus if that frame start
            # differs from the collection we want to shift the destination
            # frame indices from the source collection.
            destination_indexes = list(src_collection.indexes)
            destination_padding = len(get_first_frame_padded(src_collection))
            if repre.get("frameStart") is not None and not is_udim:
                index_frame_start = int(repre.get("frameStart"))

                render_template = anatomy.templates[template_name]
                # todo: should we ALWAYS manage the frame padding even when not
                #       having `frameStart` set?
                frame_start_padding = int(
                    render_template.get(
                        "frame_padding",
                        render_template.get("padding")
                    )
                )

                # Shift destination sequence to the start frame
                src_start_frame = next(iter(src_collection.indexes))
                shift = index_frame_start - src_start_frame
                if shift:
                    destination_indexes = [
                        frame + shift for frame in destination_indexes
                    ]
                destination_padding = frame_start_padding

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
            assert (
                len(src_collection.indexes) == len(dst_collection.indexes)
            ), "This is a bug"

            # Multiple file transfers
            transfers = []
            for src_file_name, dst in zip(src_collection, dst_collection):
                src = os.path.join(stagingdir, src_file_name)
                transfers.append((src, dst))

        else:
            # Single file
            fname = files
            assert not os.path.isabs(fname), (
                "Given file name is a full path"
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
            if not value:
                continue
            repre_context[key] = template_data[key]

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

        # Backwards compatibility:
        # Store first transferred destination as published path data
        # todo: can we remove this?
        # todo: We shouldn't change data that makes its way back into
        #       instance.data[] until we know the publish actually succeeded
        #       otherwise `published_path` might not actually be valid?
        published_path = transfers[0][1]
        repre["published_path"] = published_path  # Backwards compatibility

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

        # todo: simplify/streamline which additional data makes its way into
        #       the representation context
        if repre.get("outputName"):
            representation["context"]["output"] = repre['outputName']

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
        profile = filter_profiles(self.template_name_profiles,
                                  filter_criteria,
                                  logger=self.log)
        if profile:
            return profile["template_name"]
        else:
            return self.default_template_name

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
            "hosts": anatomy_data["app"],
            "task_types": task.get("type")
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
            "hash": openpype.api.source_hash(path),
            "sites": sites
        }


class SiteSync(object):
    """Logic for Site Sync Module functionality"""

    @classmethod
    def compute_resource_sync_sites(cls,
                                    system_settings,
                                    project_settings):
        """Get available resource sync sites"""

        def create_metadata(name, created=True):
            """Create sync site metadata for site with `name`"""
            metadata = {"name": name}
            if created:
                metadata["created_dt"] = datetime.now()
            return metadata

        default_sites = [create_metadata("studio")]

        # If sync site module is disabled return default fallback site
        system_sync_server_presets = system_settings["modules"]["sync_server"]
        log.debug("system_sett:: {}".format(system_sync_server_presets))
        if not system_sync_server_presets["enabled"]:
            return default_sites

        # If sync site module is disabled in current
        # project return default fallback site
        sync_project_presets = project_settings["global"]["sync_server"]
        if not sync_project_presets["enabled"]:
            return default_sites

        local_site, remote_site = cls._get_sites(sync_project_presets)

        # Attached sites metadata by site name
        # That is the local site, remote site, the always accesible sites
        # and their alternate sites (alias of sites with different protocol)
        attached_sites = dict()
        attached_sites[local_site] = create_metadata(local_site)

        if remote_site and remote_site != local_site:
            attached_sites[remote_site] = create_metadata(remote_site,
                                                          created=False)

        # add alternative sites
        cls._add_alternative_sites(system_sync_server_presets, attached_sites)

        # add skeleton for sites where it should be always synced to
        always_accessible_sites = (
            sync_project_presets["config"].get("always_accessible_on", [])
        )
        for site in set(always_accessible_sites):
            site = site.strip()
            if site not in attached_sites:
                attached_sites[site] = create_metadata(site, created=False)

        return list(attached_sites.values())

    @staticmethod
    def _get_sites(sync_project_presets):
        """Returns tuple (local_site, remote_site)"""
        local_site_id = openpype.api.get_local_site_id()
        local_site = sync_project_presets["config"]. \
            get("active_site", "studio").strip()

        if local_site == 'local':
            local_site = local_site_id

        remote_site = sync_project_presets["config"].get("remote_site")
        if remote_site:
            remote_site.strip()

        if remote_site == 'local':
            remote_site = local_site_id

        return local_site, remote_site

    @classmethod
    def _add_alternative_sites(cls,
                               system_sync_server_presets,
                               attached_sites):
        """Loop through all configured sites and add alternatives.

        For all sites if an alternative site is detected that has an
        accessible site then we can also register to that alternative site
        with the same "created" state. So we match the existing data.

            See SyncServerModule.handle_alternate_site
        """
        conf_sites = system_sync_server_presets.get("sites", {})
        alt_site_pairs = cls._get_alt_site_pairs(conf_sites)

        for site_name, alt_sites in alt_site_pairs.items():

            # Skip if already defined
            if site_name in attached_sites:
                continue

            # If no alternative sites we don't need to add
            if not alt_sites:
                continue

            # Take a copy of data of the first alternate site that is already
            # defined as an attached site to match the same state.
            match_meta = next((attached_sites[site] for site in alt_sites
                               if site in attached_sites), None)
            if not match_meta:
                continue

            alt_site_meta = copy.deepcopy(match_meta)
            alt_site_meta["name"] = site_name

            # Note: We change mutable `attached_site` dict in-place
            attached_sites[site_name] = alt_site_meta

    @staticmethod
    def _get_alt_site_pairs(conf_sites):
        """Returns dict of site and its alternative sites.
        If `site` has alternative site, it means that alt_site has
        'site' as
        alternative site
        Args:
            conf_sites (dict)
        Returns:
            (dict): {'site': [alternative sites]...}
        """
        alt_site_pairs = defaultdict(set)
        for site_name, site_info in conf_sites.items():
            alt_sites = set(site_info.get("alternative_sites", []))
            alt_site_pairs[site_name].update(alt_sites)

            for alt_site in alt_sites:
                alt_site_pairs[alt_site].add(site_name)

        for site_name, alt_sites in alt_site_pairs.items():
            sites_queue = deque(alt_sites)
            while sites_queue:
                alt_site = sites_queue.popleft()

                # safety against wrong config
                # {"SFTP": {"alternative_site": "SFTP"}
                if alt_site == site_name or alt_site not in alt_site_pairs:
                    continue

                for alt_alt_site in alt_site_pairs[alt_site]:
                    if (
                            alt_alt_site != site_name
                            and alt_alt_site not in alt_sites
                    ):
                        alt_sites.add(alt_alt_site)
                        sites_queue.append(alt_alt_site)

        return alt_site_pairs
