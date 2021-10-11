from importlib.abc import Loader
from ... import AbstractTemplateLoader

class BuildWorkfileTemplate:
    """Wrapper for build workfile process.

#     Load representations for current context by build presets. Build presets
#     are host related, since each host has it's loaders.
#     """

    #log = logging.getLogger("BuildWorkfile")

    def process(self):
        """Main method of this wrapper.

        Building of workfile is triggered and is possible to implement
        post processing of loaded containers if necessary.
        """
        containers = self.build_workfile()

        return containers

    @with_avalon
    def build_workfile(self):
        """Prepares and load containers into workfile.

        Loads latest versions of current and linked assets to workfile by logic
        stored in Workfile profiles from presets. Profiles are set by host,
        filtered by current task name and used by families.

        Each family can specify representation names and loaders for
        representations and first available and successful loaded
        representation is returned as container.

        At the end you'll get list of loaded containers per each asset.

        loaded_containers [{
            "asset_entity": <AssetEntity1>,
            "containers": [<Container1>, <Container2>, ...]
        }, {
            "asset_entity": <AssetEntity2>,
            "containers": [<Container3>, ...]
        }, {
            ...
        }]
        """
        # Get current asset name and entity
        current_asset_name = avalon.io.Session["AVALON_ASSET"]
        current_asset_entity = avalon.io.find_one({
            "type": "asset",
            "name": current_asset_name
        })

        # Skip if asset was not found
        if not current_asset_entity:
            print("Asset entity with name `{}` was not found".format(
                current_asset_name
            ))
            return
        current_task = current_asset_entity['task']
        ConcreteLoader = TemplateLoader
        template_loader = ConcreteLoader(current_task)

        context_assets, linked_assets = template_loader.load_template()

        #Prepare available loaders
        loaders_by_name = {}
        for loader in avalon.api.discover(avalon.api.Loader):
            loader_name = loader.__name__
            if loader_name in loaders_by_name:
                raise KeyError(
                    "Duplicated loader name {0}!".format(loader_name)
                )
            loaders_by_name[loader_name] = loader

        # Skip if there are any loaders
        if not loaders_by_name:
            self.log.warning("There are no registered loaders.")
            return

        # Get current task name
        current_task_name = avalon.io.Session["AVALON_TASK"]

        # Load workfile presets for task
        self.build_presets = self.get_build_presets(
            current_task_name, current_asset_entity
        )

        # Skip if there are any presets for task
        if not self.build_presets:
            self.log.warning(
                "Current task `{}` does not have any loading preset.".format(
                    current_task_name
                )
            )
            return

        # Get presets for loading current asset
        current_context_profiles = self.build_presets.get("current_context")
        # Get presets for loading linked assets
        link_context_profiles = self.build_presets.get("linked_assets")
        # Skip if both are missing
        if not current_context_profiles and not link_context_profiles:
            self.log.warning(
                "Current task `{}` has empty loading preset.".format(
                    current_task_name
                )
            )
            return

        elif not current_context_profiles:
            self.log.warning((
                "Current task `{}` doesn't have any loading"
                " preset for it's context."
            ).format(current_task_name))

        elif not link_context_profiles:
            self.log.warning((
                "Current task `{}` doesn't have any"
                "loading preset for it's linked assets."
            ).format(current_task_name))

        # Prepare assets to process by workfile presets
        assets = []
        current_asset_id = None
        if current_context_profiles:
            # Add current asset entity if preset has current context set
            assets.append(current_asset_entity)
            current_asset_id = current_asset_entity["_id"]

        if link_context_profiles:
            # Find and append linked assets if preset has set linked mapping
            link_assets = get_linked_assets(current_asset_entity)
            if link_assets:
                assets.extend(link_assets)

        # Skip if there are no assets. This can happen if only linked mapping
        # is set and there are no links for his asset.
        if not assets:
            self.log.warning(
                "Asset does not have linked assets. Nothing to process."
            )
            return

        # Prepare entities from database for assets
        prepared_entities = self._collect_last_version_repres(assets)

        # Load containers by prepared entities and presets
        loaded_containers = []
        # - Current asset containers
        if current_asset_id and current_asset_id in prepared_entities:
            current_context_data = prepared_entities.pop(current_asset_id)
            loaded_data = self.load_containers_by_asset_data(
                current_context_data, current_context_profiles, loaders_by_name
            )
            if loaded_data:
                loaded_containers.append(loaded_data)

        # - Linked assets container
        for linked_asset_data in prepared_entities.values():
            loaded_data = self.load_containers_by_asset_data(
                linked_asset_data, link_context_profiles, loaders_by_name
            )
            if loaded_data:
                loaded_containers.append(loaded_data)

        # Return list of loaded containers
        return loaded_containers








# class BuildWorkfile:
#     """Wrapper for build workfile process.

#     Load representations for current context by build presets. Build presets
#     are host related, since each host has it's loaders.
#     """

#     log = logging.getLogger("BuildWorkfile")

#     @staticmethod
#     def map_subsets_by_family(subsets):
#         subsets_by_family = collections.defaultdict(list)
#         for subset in subsets:
#             family = subset["data"].get("family")
#             if not family:
#                 families = subset["data"].get("families")
#                 if not families:
#                     continue
#                 family = families[0]

#             subsets_by_family[family].append(subset)
#         return subsets_by_family

#     def process(self):
#         """Main method of this wrapper.

#         Building of workfile is triggered and is possible to implement
#         post processing of loaded containers if necessary.
#         """
#         containers = self.build_workfile()

#         return containers

#     @with_avalon
#     def build_workfile(self):
#         """Prepares and load containers into workfile.

#         Loads latest versions of current and linked assets to workfile by logic
#         stored in Workfile profiles from presets. Profiles are set by host,
#         filtered by current task name and used by families.

#         Each family can specify representation names and loaders for
#         representations and first available and successful loaded
#         representation is returned as container.

#         At the end you'll get list of loaded containers per each asset.

#         loaded_containers [{
#             "asset_entity": <AssetEntity1>,
#             "containers": [<Container1>, <Container2>, ...]
#         }, {
#             "asset_entity": <AssetEntity2>,
#             "containers": [<Container3>, ...]
#         }, {
#             ...
#         }]
#         """

#         # Prepare available loaders
#         loaders_by_name = {}
#         for loader in avalon.api.discover(avalon.api.Loader):
#             loader_name = loader.__name__
#             if loader_name in loaders_by_name:
#                 raise KeyError(
#                     "Duplicated loader name {0}!".format(loader_name)
#                 )
#             loaders_by_name[loader_name] = loader

#         # Skip if there are any loaders
#         if not loaders_by_name:
#             self.log.warning("There are no registered loaders.")
#             return

#         template_loader = loaders_by_name.get('TemplateLoader')

#         # Skip if there are not template loaders
#         if not template_loader:
#             self.log.error("There are no registered template loader.")
#             return
#         #avalon.api.load(template_loader, current_asset_entity['_id'])

#         #self.load_template(template_loader)
#         print("0", loaders_by_name)
#         print("$"*50)
#         print(1, template_loader)
#         print(2, dir(template_loader))
#         temp_loader = template_loader()
#         temp_loader.load({})

#         # Get current task name
#         current_task_name = avalon.io.Session["AVALON_TASK"]

#         # Load workfile presets for task
#         self.build_presets = self.get_build_presets(
#             current_task_name, current_asset_entity
#         )

#         # Skip if there are any presets for task
#         if not self.build_presets:
#             self.log.warning(
#                 "Current task `{}` does not have any loading preset.".format(
#                     current_task_name
#                 )
#             )
#             return

#         # Get presets for loading current asset
#         current_context_profiles = self.build_presets.get("current_context")
#         # Get presets for loading linked assets
#         link_context_profiles = self.build_presets.get("linked_assets")
#         # Skip if both are missing
#         if not current_context_profiles and not link_context_profiles:
#             self.log.warning(
#                 "Current task `{}` has empty loading preset.".format(
#                     current_task_name
#                 )
#             )
#             return

#         elif not current_context_profiles:
#             self.log.warning((
#                 "Current task `{}` doesn't have any loading"
#                 " preset for it's context."
#             ).format(current_task_name))

#         elif not link_context_profiles:
#             self.log.warning((
#                 "Current task `{}` doesn't have any"
#                 "loading preset for it's linked assets."
#             ).format(current_task_name))

#         # Prepare assets to process by workfile presets
#         assets = []
#         current_asset_id = None
#         if current_context_profiles:
#             # Add current asset entity if preset has current context set
#             assets.append(current_asset_entity)
#             current_asset_id = current_asset_entity["_id"]

#         if link_context_profiles:
#             # Find and append linked assets if preset has set linked mapping
#             link_assets = get_linked_assets(current_asset_entity)
#             if link_assets:
#                 assets.extend(link_assets)

#         # Skip if there are no assets. This can happen if only linked mapping
#         # is set and there are no links for his asset.
#         if not assets:
#             self.log.warning(
#                 "Asset does not have linked assets. Nothing to process."
#             )
#             return

#         # Prepare entities from database for assets
#         prepared_entities = self._collect_last_version_repres(assets)

#         # Load containers by prepared entities and presets
#         loaded_containers = []
#         # - Current asset containers
#         if current_asset_id and current_asset_id in prepared_entities:
#             current_context_data = prepared_entities.pop(current_asset_id)
#             loaded_data = self.load_containers_by_asset_data(
#                 current_context_data, current_context_profiles, loaders_by_name
#             )
#             if loaded_data:
#                 loaded_containers.append(loaded_data)

#         # - Linked assets container
#         for linked_asset_data in prepared_entities.values():
#             loaded_data = self.load_containers_by_asset_data(
#                 linked_asset_data, link_context_profiles, loaders_by_name
#             )
#             if loaded_data:
#                 loaded_containers.append(loaded_data)

#         # Return list of loaded containers
#         return loaded_containers

#     @with_avalon
#     def get_build_presets(self, task_name, asset_doc):
#         """ Returns presets to build workfile for task name.

#         Presets are loaded for current project set in
#         io.Session["AVALON_PROJECT"], filtered by registered host
#         and entered task name.

#         Args:
#             task_name (str): Task name used for filtering build presets.

#         Returns:
#             (dict): preset per entered task name
#         """
#         host_name = avalon.api.registered_host().__name__.rsplit(".", 1)[-1]
#         project_settings = get_project_settings(
#             avalon.io.Session["AVALON_PROJECT"]
#         )

#         host_settings = project_settings.get(host_name) or {}
#         # Get presets for host
#         wb_settings = host_settings.get("workfile_builder")
#         if not wb_settings:
#             # backward compatibility
#             wb_settings = host_settings.get("workfile_build") or {}

#         builder_profiles = wb_settings.get("profiles")
#         if not builder_profiles:
#             return None

#         task_type = (
#             asset_doc
#             .get("data", {})
#             .get("tasks", {})
#             .get(task_name, {})
#             .get("type")
#         )
#         filter_data = {
#             "task_types": task_type,
#             "tasks": task_name
#         }
#         return filter_profiles(builder_profiles, filter_data)

#     def _filter_build_profiles(self, build_profiles, loaders_by_name):
#         """ Filter build profiles by loaders and prepare process data.

#         Valid profile must have "loaders", "families" and "repre_names" keys
#         with valid values.
#         - "loaders" expects list of strings representing possible loaders.
#         - "families" expects list of strings for filtering
#                      by main subset family.
#         - "repre_names" expects list of strings for filtering by
#                         representation name.

#         Lowered "families" and "repre_names" are prepared for each profile with
#         all required keys.

#         Args:
#             build_profiles (dict): Profiles for building workfile.
#             loaders_by_name (dict): Available loaders per name.

#         Returns:
#             (list): Filtered and prepared profiles.
#         """
#         valid_profiles = []
#         for profile in build_profiles:
#             # Check loaders
#             profile_loaders = profile.get("loaders")
#             if not profile_loaders:
#                 self.log.warning((
#                     "Build profile has missing loaders configuration: {0}"
#                 ).format(json.dumps(profile, indent=4)))
#                 continue

#             # Check if any loader is available
#             loaders_match = False
#             for loader_name in profile_loaders:
#                 if loader_name in loaders_by_name:
#                     loaders_match = True
#                     break

#             if not loaders_match:
#                 self.log.warning((
#                     "All loaders from Build profile are not available: {0}"
#                 ).format(json.dumps(profile, indent=4)))
#                 continue

#             # Check families
#             profile_families = profile.get("families")
#             if not profile_families:
#                 self.log.warning((
#                     "Build profile is missing families configuration: {0}"
#                 ).format(json.dumps(profile, indent=4)))
#                 continue

#             # Check representation names
#             profile_repre_names = profile.get("repre_names")
#             if not profile_repre_names:
#                 self.log.warning((
#                     "Build profile is missing"
#                     " representation names filtering: {0}"
#                 ).format(json.dumps(profile, indent=4)))
#                 continue

#             # Prepare lowered families and representation names
#             profile["families_lowered"] = [
#                 fam.lower() for fam in profile_families
#             ]
#             profile["repre_names_lowered"] = [
#                 name.lower() for name in profile_repre_names
#             ]

#             valid_profiles.append(profile)

#         return valid_profiles

#     def _prepare_profile_for_subsets(self, subsets, profiles):
#         """Select profile for each subset byt it's data.

#         Profiles are filtered for each subset individually.
#         Profile is filtered by subset's family, optionally by name regex and
#         representation names set in profile.
#         It is possible to not find matching profile for subset, in that case
#         subset is skipped and it is possible that none of subsets have
#         matching profile.

#         Args:
#             subsets (list): Subset documents.
#             profiles (dict): Build profiles.

#         Returns:
#             (dict) Profile by subset's id.
#         """
#         # Prepare subsets
#         subsets_by_family = self.map_subsets_by_family(subsets)

#         profiles_per_subset_id = {}
#         for family, subsets in subsets_by_family.items():
#             family_low = family.lower()
#             for profile in profiles:
#                 # Skip profile if does not contain family
#                 if family_low not in profile["families_lowered"]:
#                     continue

#                 # Precompile name filters as regexes
#                 profile_regexes = profile.get("subset_name_filters")
#                 if profile_regexes:
#                     _profile_regexes = []
#                     for regex in profile_regexes:
#                         _profile_regexes.append(re.compile(regex))
#                     profile_regexes = _profile_regexes

#                 # TODO prepare regex compilation
#                 for subset in subsets:
#                     # Verify regex filtering (optional)
#                     if profile_regexes:
#                         valid = False
#                         for pattern in profile_regexes:
#                             if re.match(pattern, subset["name"]):
#                                 valid = True
#                                 break

#                         if not valid:
#                             continue

#                     profiles_per_subset_id[subset["_id"]] = profile

#                 # break profiles loop on finding the first matching profile
#                 break
#         return profiles_per_subset_id

#     def load_containers_by_asset_data(
#         self, asset_entity_data, build_profiles, loaders_by_name
#     ):
#         """Load containers for entered asset entity by Build profiles.

#         Args:
#             asset_entity_data (dict): Prepared data with subsets, last version
#                 and representations for specific asset.
#             build_profiles (dict): Build profiles.
#             loaders_by_name (dict): Available loaders per name.

#         Returns:
#             (dict) Output contains asset document and loaded containers.
#         """

#         # Make sure all data are not empty
#         if not asset_entity_data or not build_profiles or not loaders_by_name:
#             return

#         asset_entity = asset_entity_data["asset_entity"]

#         valid_profiles = self._filter_build_profiles(
#             build_profiles, loaders_by_name
#         )
#         if not valid_profiles:
#             self.log.warning(
#                 "There are not valid Workfile profiles. Skipping process."
#             )
#             return

#         self.log.debug("Valid Workfile profiles: {}".format(valid_profiles))

#         subsets_by_id = {}
#         version_by_subset_id = {}
#         repres_by_version_id = {}
#         for subset_id, in_data in asset_entity_data["subsets"].items():
#             subset_entity = in_data["subset_entity"]
#             subsets_by_id[subset_entity["_id"]] = subset_entity

#             version_data = in_data["version"]
#             version_entity = version_data["version_entity"]
#             version_by_subset_id[subset_id] = version_entity
#             repres_by_version_id[version_entity["_id"]] = (
#                 version_data["repres"]
#             )

#         if not subsets_by_id:
#             self.log.warning("There are not subsets for asset {0}".format(
#                 asset_entity["name"]
#             ))
#             return

#         profiles_per_subset_id = self._prepare_profile_for_subsets(
#             subsets_by_id.values(), valid_profiles
#         )
#         if not profiles_per_subset_id:
#             self.log.warning("There are not valid subsets.")
#             return

#         valid_repres_by_subset_id = collections.defaultdict(list)
#         for subset_id, profile in profiles_per_subset_id.items():
#             profile_repre_names = profile["repre_names_lowered"]

#             version_entity = version_by_subset_id[subset_id]
#             version_id = version_entity["_id"]
#             repres = repres_by_version_id[version_id]
#             for repre in repres:
#                 repre_name_low = repre["name"].lower()
#                 if repre_name_low in profile_repre_names:
#                     valid_repres_by_subset_id[subset_id].append(repre)

#         # DEBUG message
#         msg = "Valid representations for Asset: `{}`".format(
#             asset_entity["name"]
#         )
#         for subset_id, repres in valid_repres_by_subset_id.items():
#             subset = subsets_by_id[subset_id]
#             msg += "\n# Subset Name/ID: `{}`/{}".format(
#                 subset["name"], subset_id
#             )
#             for repre in repres:
#                 msg += "\n## Repre name: `{}`".format(repre["name"])

#         self.log.debug(msg)

#         containers = self._load_containers(
#             valid_repres_by_subset_id, subsets_by_id,
#             profiles_per_subset_id, loaders_by_name
#         )

#         return {
#             "asset_entity": asset_entity,
#             "containers": containers
#         }

#     @with_avalon
#     def _load_containers(
#         self, repres_by_subset_id, subsets_by_id,
#         profiles_per_subset_id, loaders_by_name
#     ):
#         """Real load by collected data happens here.

#         Loading of representations per subset happens here. Each subset can
#         loads one representation. Loading is tried in specific order.
#         Representations are tried to load by names defined in configuration.
#         If subset has representation matching representation name each loader
#         is tried to load it until any is successful. If none of them was
#         successful then next reprensentation name is tried.
#         Subset process loop ends when any representation is loaded or
#         all matching representations were already tried.

#         Args:
#             repres_by_subset_id (dict): Available representations mapped
#                 by their parent (subset) id.
#             subsets_by_id (dict): Subset documents mapped by their id.
#             profiles_per_subset_id (dict): Build profiles mapped by subset id.
#             loaders_by_name (dict): Available loaders per name.

#         Returns:
#             (list) Objects of loaded containers.
#         """
#         loaded_containers = []

#         # Get subset id order from build presets.
#         build_presets = self.build_presets.get("current_context", [])
#         build_presets += self.build_presets.get("linked_assets", [])
#         subset_ids_ordered = []
#         for preset in build_presets:
#             for preset_family in preset["families"]:
#                 for id, subset in subsets_by_id.items():
#                     if preset_family not in subset["data"].get("families", []):
#                         continue

#                     subset_ids_ordered.append(id)

#         # Order representations from subsets.
#         print("repres_by_subset_id", repres_by_subset_id)
#         representations_ordered = []
#         representations = []
#         for id in subset_ids_ordered:
#             for subset_id, repres in repres_by_subset_id.items():
#                 if repres in representations:
#                     continue

#                 if id == subset_id:
#                     representations_ordered.append((subset_id, repres))
#                     representations.append(repres)

#         print("representations", representations)

#         # Load ordered reprensentations.
#         for subset_id, repres in representations_ordered:
#             subset_name = subsets_by_id[subset_id]["name"]

#             profile = profiles_per_subset_id[subset_id]
#             loaders_last_idx = len(profile["loaders"]) - 1
#             repre_names_last_idx = len(profile["repre_names_lowered"]) - 1

#             repre_by_low_name = {
#                 repre["name"].lower(): repre for repre in repres
#             }

#             is_loaded = False
#             for repre_name_idx, profile_repre_name in enumerate(
#                 profile["repre_names_lowered"]
#             ):
#                 # Break iteration if representation was already loaded
#                 if is_loaded:
#                     break

#                 repre = repre_by_low_name.get(profile_repre_name)
#                 if not repre:
#                     continue

#                 for loader_idx, loader_name in enumerate(profile["loaders"]):
#                     if is_loaded:
#                         break

#                     loader = loaders_by_name.get(loader_name)
#                     if not loader:
#                         continue
#                     try:
#                         container = avalon.api.load(
#                             loader,
#                             repre["_id"],
#                             name=subset_name
#                         )
#                         loaded_containers.append(container)
#                         is_loaded = True

#                     except Exception as exc:
#                         if exc == avalon.pipeline.IncompatibleLoaderError:
#                             self.log.info((
#                                 "Loader `{}` is not compatible with"
#                                 " representation `{}`"
#                             ).format(loader_name, repre["name"]))

#                         else:
#                             self.log.error(
#                                 "Unexpected error happened during loading",
#                                 exc_info=True
#                             )

#                         msg = "Loading failed."
#                         if loader_idx < loaders_last_idx:
#                             msg += " Trying next loader."
#                         elif repre_name_idx < repre_names_last_idx:
#                             msg += (
#                                 " Loading of subset `{}` was not successful."
#                             ).format(subset_name)
#                         else:
#                             msg += " Trying next representation."
#                         self.log.info(msg)

#         return loaded_containers

#     @with_avalon
#     def _collect_last_version_repres(self, asset_entities):
#         """Collect subsets, versions and representations for asset_entities.

#         Args:
#             asset_entities (list): Asset entities for which want to find data

#         Returns:
#             (dict): collected entities

#         Example output:
#         ```
#         {
#             {Asset ID}: {
#                 "asset_entity": <AssetEntity>,
#                 "subsets": {
#                     {Subset ID}: {
#                         "subset_entity": <SubsetEntity>,
#                         "version": {
#                             "version_entity": <VersionEntity>,
#                             "repres": [
#                                 <RepreEntity1>, <RepreEntity2>, ...
#                             ]
#                         }
#                     },
#                     ...
#                 }
#             },
#             ...
#         }
#         output[asset_id]["subsets"][subset_id]["version"]["repres"]
#         ```
#         """

#         if not asset_entities:
#             return {}

#         asset_entity_by_ids = {asset["_id"]: asset for asset in asset_entities}

#         subsets = list(avalon.io.find({
#             "type": "subset",
#             "parent": {"$in": asset_entity_by_ids.keys()}
#         }))
#         subset_entity_by_ids = {subset["_id"]: subset for subset in subsets}

#         sorted_versions = list(avalon.io.find({
#             "type": "version",
#             "parent": {"$in": subset_entity_by_ids.keys()}
#         }).sort("name", -1))

#         subset_id_with_latest_version = []
#         last_versions_by_id = {}
#         for version in sorted_versions:
#             subset_id = version["parent"]
#             if subset_id in subset_id_with_latest_version:
#                 continue
#             subset_id_with_latest_version.append(subset_id)
#             last_versions_by_id[version["_id"]] = version

#         repres = avalon.io.find({
#             "type": "representation",
#             "parent": {"$in": last_versions_by_id.keys()}
#         })

#         output = {}
#         for repre in repres:
#             version_id = repre["parent"]
#             version = last_versions_by_id[version_id]

#             subset_id = version["parent"]
#             subset = subset_entity_by_ids[subset_id]

#             asset_id = subset["parent"]
#             asset = asset_entity_by_ids[asset_id]

#             if asset_id not in output:
#                 output[asset_id] = {
#                     "asset_entity": asset,
#                     "subsets": {}
#                 }

#             if subset_id not in output[asset_id]["subsets"]:
#                 output[asset_id]["subsets"][subset_id] = {
#                     "subset_entity": subset,
#                     "version": {
#                         "version_entity": version,
#                         "repres": []
#                     }
#                 }

#             output[asset_id]["subsets"][subset_id]["version"]["repres"].append(
#                 repre
#             )

#         return output