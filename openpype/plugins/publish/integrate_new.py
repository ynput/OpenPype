import os
import logging
import sys
import copy
import clique
import six

from bson.objectid import ObjectId
from pymongo import DeleteOne, InsertOne, UpdateOne
import pyblish.api
from avalon import io
import openpype.api
from datetime import datetime
from openpype.lib.profiles_filtering import filter_profiles
from openpype.lib.file_transaction import FileTransaction

log = logging.getLogger(__name__)


def get_frame_padded(frame, padding):
    """Return frame number as string with `padding` amount of padded zeros"""
    return "{frame:0{padding}d}".format(padding=padding, frame=frame)


def get_first_frame_padded(collection):
    """Return first frame as padded number from `clique.Collection`"""
    start_frame = next(iter(collection.indexes))
    return get_frame_padded(start_frame, padding=collection.padding)


class IntegrateAssetNew(pyblish.api.InstancePlugin):
    """Resolve any dependency issues

    This plug-in resolves any paths which, if not updated might break
    the published file.

    The order of families is important, when working with lookdev you want to
    first publish the texture, update the texture paths in the nodes and then
    publish the shading network. Same goes for file dependent assets.

    Requirements for instance to be correctly integrated

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
                "usd"
                ]
    exclude_families = ["clip"]
    db_representation_context_keys = [
        "project", "asset", "task", "subset", "version", "representation",
        "family", "hierarchy", "task", "username", "frame"
    ]
    default_template_name = "publish"

    # Attributes set by settings
    template_name_profiles = None

    def process(self, instance):

        # Exclude instances that also contain families from exclude families
        families = set(self._get_instance_families(instance))
        if families & set(self.exclude_families):
            return

        file_transactions = FileTransaction(log=self.log)
        try:
            self.register(instance, file_transactions)
        except Exception:
            # clean destination
            # todo: rollback any registered entities? (or how safe are we?)
            file_transactions.rollback()
            self.log.critical("Error when registering", exc_info=True)
            six.reraise(*sys.exc_info())

        # Finalizing can't rollback safely so no use for moving it to
        # the try, except.
        file_transactions.finalize()

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

        # Ensure at least one file is set up for transfer in staging dir.
        repres = instance.data.get("representations")
        assert repres, "Instance has no files to transfer"
        assert isinstance(repres, (list, tuple)), (
            "Instance 'files' must be a list, got: {0} {1}".format(
                str(type(repres)), str(repres)
            )
        )

        template_name = self._get_template_name(instance)

        subset = self.register_subset(instance)

        version = self.register_version(instance, subset)
        instance.data["versionEntity"] = version

        archived_repres = list(io.find({
            "parent": version["_id"],
            "type": "archived_representation"
        }))

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
                                                   archived_repres,
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
        for src, dst in instance.data.get("transfers", []):
            file_transactions.add(src, dst, mode=FileTransaction.MODE_COPY)
        for src, dst in instance.data.get("hardlinks", []):
            file_transactions.add(src, dst, mode=FileTransaction.MODE_HARDLINK)

        # Process all file transfers of all integrations now
        self.log.debug("Integrating source files to destination ...")
        file_transactions.process()
        self.log.debug("Backup files "
                       "{}".format(file_transactions.backups))
        self.log.debug("Integrated files "
                       "{}".format(file_transactions.transferred))

        # Finalize the representations now the published files are integrated
        # Get 'files' info for representations and its attached resources
        self.log.debug("Retrieving Representation files information ...")
        sites = SiteSync.compute_resource_sync_sites(
            system_settings=instance.context.data["system_settings"],
            project_settings=instance.context.data["project_settings"]
        )
        log.debug("final sites:: {}".format(sites))

        anatomy = instance.context.data["anatomy"]
        representations = []
        for prepared in prepared_representations:
            transfers = prepared["transfers"]
            representation = prepared["representation"]
            representation["files"] = self.get_files_info(
                transfers, sites, anatomy
            )
            representations.append(representation)

        # Remove all archived representations
        if archived_repres:
            repre_ids_to_remove = [repre["_id"] for repre in archived_repres]
            io.delete_many({"_id": {"$in": repre_ids_to_remove}})

        # Write the new representations to the database
        io.insert_many(representations)

        # Backwards compatibility
        # todo: can we avoid the need to store this?
        instance.data["published_representations"] = {
            p["representation"]["_id"]: p for p in prepared_representations
        }

        self.log.info("Registered {} representations"
                      "".format(len(representations)))

    def register_version(self, instance, subset):

        version_number = instance.data["version"]
        self.log.debug("Version: v{0:03d}".format(version_number))

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
        })

        bulk_writes = []
        if existing_version is None:
            self.log.debug("Creating new version ...")
            version["_id"] = ObjectId()
            bulk_writes.append(InsertOne(version))
        else:
            self.log.debug("Updating existing version ...")
            # Check if instance have set `append` mode which cause that
            # only replicated representations are set to archive
            append_repres = instance.data.get("append", False)

            # Update version data
            version_id = existing_version['_id']
            bulk_writes.append(UpdateOne({
                '_id': version_id
            }, {
                '$set': version
            }))

            # Instead of directly writing and querying we reproduce what
            # the resulting version would look like so we can hold off making
            # changes to the database to avoid the need for 'rollback'
            version = copy.deepcopy(version)
            version["_id"] = existing_version["_id"]

            # Find representations of existing version and archive them
            repres = instance.data.get("representations", [])
            new_repre_names_low = [_repre["name"].lower() for _repre in repres]
            current_repres = io.find({
                "type": "representation",
                "parent": version_id
            })
            for repre in current_repres:
                if append_repres:
                    # archive only duplicated representations
                    if repre["name"].lower() not in new_repre_names_low:
                        continue
                # Representation must change type,
                # `_id` must be stored to other key and replaced with new
                # - that is because new representations should have same ID
                repre_id = repre["_id"]
                bulk_writes.append(DeleteOne({"_id": repre_id}))

                repre["orig_id"] = repre_id
                repre["_id"] = ObjectId()
                repre["type"] = "archived_representation"
                bulk_writes.append(InsertOne(repre))

        # bulk updates
        # todo: Try to avoid writing already until after we've prepared
        #       representations to allow easier rollback?
        io._database[io.Session["AVALON_PROJECT"]].bulk_write(
            bulk_writes
        )

        self.log.info("Registered version: v{0:03d}".format(version["name"]))

        return version

    def prepare_representation(self, repre,
                               template_name,
                               archived_repres,
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
        for representation_key, anatomy_key in {
            # Representation Key: Anatomy data key
            "resolutionWidth": "resolution_width",
            "resolutionHeight": "resolution_height",
            "fps": "fps",
            "outputName": "output",
        }.items():
            value = repre.get(representation_key)
            if value:
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

        is_sequence_representation = isinstance(files, (list, tuple))
        if is_sequence_representation:
            # Collection of files (sequence)
            # Get the sequence as a collection. The files must be of a single
            # sequence and have no remainder outside of the collections.
            collections, remainder = clique.assemble(files,
                                                     minimum_items=1)
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
            src_collection = collections[0]

            # If the representation has `frameStart` set it renumbers the
            # frame indices of the published collection. It will start from
            # that `frameStart` index instead. Thus if that frame start
            # differs from the collection we want to shift the destination
            # frame indices from the source collection.
            destination_indexes = list(src_collection.indexes)
            destination_padding = len(get_first_frame_padded(src_collection))
            if repre.get("frameStart") is not None:
                index_frame_start = int(repre.get("frameStart"))

                # TODO use frame padding from right template group
                render_template = anatomy.templates["render"]
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
            if repre.get("udim"):
                # UDIM representations handle ranges in a different manner
                template_data["udim"] = first_index_padded
            else:
                template_data["frame"] = first_index_padded

            # Construct destination collection from template
            anatomy_filled = anatomy.format(template_data)
            template_filled = anatomy_filled[template_name]["path"]
            repre_context = template_filled.used_values
            self.log.debug("Template filled: {}".format(str(template_filled)))
            dst_collections, _remainder = clique.assemble(
                [os.path.normpath(template_filled)],
                minimum_items=1,
                patterns=[clique.PATTERNS["frames"]]
            )
            assert not _remainder, "This is a bug"
            assert len(dst_collections) == 1, "This is a bug"
            dst_collection = dst_collections[0]

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
            template_data.pop("frame", None)
            fname = files
            assert not os.path.isabs(fname), (
                "Given file name is a full path"
            )
            # Store used frame value to template data
            if repre.get("udim"):
                template_data["udim"] = repre["udim"][0]
            src = os.path.join(stagingdir, fname)
            anatomy_filled = anatomy.format(template_data)
            template_filled = anatomy_filled[template_name]["path"]
            repre_context = template_filled.used_values
            dst = os.path.normpath(template_filled)

            # Single file transfer
            transfers = [(src, dst)]

        for key in self.db_representation_context_keys:
            value = template_data.get(key)
            if not value:
                continue
            repre_context[key] = template_data[key]

        # Explicitly store the full list even though template data might
        # have a different value
        if repre.get("udim"):
            repre_context["udim"] = repre.get("udim")  # store list

        # Define representation id
        repre_id = ObjectId()

        # Use previous representation's id if there is a name match
        repre_name_lower = repre["name"].lower()
        for _archived_repres in archived_repres:
            if repre_name_lower == _archived_repres["name"].lower():
                repre_id = _archived_repres["orig_id"]
                break

        # Backwards compatibility:
        # Store first transferred destination as published path data
        # todo: can we remove this?
        published_path = transfers[0][1]
        repre["published_path"] = published_path  # Backwards compatibility

        # todo: `repre` is not the actual `representation` entity
        #       we should simplify/clarify difference between data above
        #       and the actual representation entity for the database
        data = repre.get("data") or {}
        data.update({'path': published_path, 'template': template})
        representation = {
            "_id": repre_id,
            "schema": "openpype:representation-2.0",
            "type": "representation",
            "parent": version["_id"],
            "name": repre['name'],
            "data": data,
            "dependencies": instance.data.get("dependencies", "").split(),

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

    def _get_instance_families(self, instance):
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

    def _get_template_name(self, instance):
        """Return anatomy template name to use for integration"""

        # Define publish template name from profiles
        filter_criteria = self.get_profile_filter_criteria(instance)
        profile = filter_profiles(self.template_name_profiles,
                                  filter_criteria,
                                  logger=self.log)
        template_name = self.default_template_name
        if profile:
            template_name = profile["template_name"]
        return template_name

    def register_subset(self, instance):
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
            "families": self._get_instance_families(instance)
        }

        subset_group = instance.data.get("subsetGroup")
        if subset_group:
            data["subsetGroup"] = subset_group

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
            io.insert_one(subset)

        else:
            # Update existing subset data with new data and set in database.
            # We also change the found subset  in-place so we don't need to
            # re-query the subset afterwards
            subset["data"].update(data)
            io.update_many(
                {"type": "subset", "_id": subset["_id"]},
                {"$set": {
                    "data": subset["data"]
                }}
            )

        self.log.info("Registered subset: {}".format(subset_name))
        return subset

    def create_version_data(self, instance):
        """Create the data collection for the version

        Args:
            instance: the current instance being published

        Returns:
            dict: the required information with instance.data as key
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
            "families": self._get_instance_families(instance),
            "time": context.data["time"],
            "author": context.data["user"],
            "source": source,
            "comment": context.data.get("comment"),
            "machine": context.data.get("machine"),
            "fps": context.data.get(
                "fps", instance.data.get("fps")
            )
        }

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

    def main_family_from_instance(self, instance):
        """Returns main family of entered instance."""
        return self._get_instance_families(instance)[0]

    def get_rootless_path(self, anatomy, path):
        """  Returns, if possible, path without absolute portion from host
             (eg. 'c:\' or '/opt/..')
             This information is host dependent and shouldn't be captured.
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
        success, rootless_path = (
            anatomy.find_root_template_from_path(path)
        )
        if success:
            path = rootless_path
        else:
            self.log.warning((
                "Could not find root path for remapping \"{}\"."
                " This may cause issues on farm."
            ).format(path))
        return path

    def get_files_info(self, transfers, sites, anatomy):
        """ Prepare 'files' portion for attached resources and main asset.
            Combining records from 'transfers' and 'hardlinks' parts from
            instance.
            All attached resources should be added, currently without
            Context info.

        Arguments:
            instance: the current instance being published
            integrated_file_sizes: dictionary of destination path (absolute)
            and its file size
        Returns:
            output_resources: array of dictionaries to be added to 'files' key
            in representation
        """
        file_infos = []
        for _src, dest in transfers:
            file_info = self.prepare_file_info(dest, anatomy, sites=sites)
            file_infos.append(file_info)

        return file_infos

    def prepare_file_info(self, path, anatomy, sites):
        """ Prepare information for one file (asset or resource)

        Arguments:
            path: destination url of published file (rootless)
            size(optional): size of file in bytes
            file_hash(optional): hash of file for synchronization validation
            sites(optional): array of published locations,
                            [ {'name':'studio', 'created_dt':date} by default
                                keys expected ['studio', 'site1', 'gdrive1']
        Returns:
            rec: dictionary with filled info
        """
        file_hash = openpype.api.source_hash(path)

        return {
            "_id": ObjectId(),
            "path": self.get_rootless_path(anatomy, path),
            "size": os.path.getsize(path),
            "hash": file_hash,
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

        # add skeleton for sites where it should be always synced to
        always_accessible_sites = (
            sync_project_presets["config"].get("always_accessible_on", [])
        )
        for site in always_accessible_sites:
            site = site.strip()
            if site not in attached_sites:
                attached_sites[site] = create_metadata(site, created=False)

        # add alternative sites
        cls._add_alternative_sites(system_sync_server_presets, attached_sites)

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

    @staticmethod
    def _add_alternative_sites(system_sync_server_presets,
                               attached_sites):
        """Loop through all configured sites and add alternatives.

        For all sites if an alternative site is detected that has an
        accessible site then we can also register to that alternative site
        with the same "created" state. So we match the existing data.

            See SyncServerModule.handle_alternate_site
        """
        conf_sites = system_sync_server_presets.get("sites", {})

        for site_name, site_info in conf_sites.items():

            # Skip if already defined
            if site_name in attached_sites:
                continue

            # Get alternate sites (stripped names) for this site name
            alt_sites = site_info.get("alternative_sites", [])
            alt_sites = [site.strip() for site in alt_sites]
            alt_sites = set(alt_sites)

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
