import os
import sys
import six
import pyblish.api
import clique


class IntegrateFtrackApi(pyblish.api.InstancePlugin):
    """ Commit components to server. """

    order = pyblish.api.IntegratorOrder+0.499
    label = "Integrate Ftrack Api"
    families = ["ftrack"]

    def query(self, entitytype, data):
        """ Generate a query expression from data supplied.

        If a value is not a string, we'll add the id of the entity to the
        query.

        Args:
            entitytype (str): The type of entity to query.
            data (dict): The data to identify the entity.
            exclusions (list): All keys to exclude from the query.

        Returns:
            str: String query to use with "session.query"
        """
        queries = []
        if sys.version_info[0] < 3:
            for key, value in data.iteritems():
                if not isinstance(value, (basestring, int)):
                    self.log.info("value: {}".format(value))
                    if "id" in value.keys():
                        queries.append(
                            "{0}.id is \"{1}\"".format(key, value["id"])
                        )
                else:
                    queries.append("{0} is \"{1}\"".format(key, value))
        else:
            for key, value in data.items():
                if not isinstance(value, (str, int)):
                    self.log.info("value: {}".format(value))
                    if "id" in value.keys():
                        queries.append(
                            "{0}.id is \"{1}\"".format(key, value["id"])
                        )
                else:
                    queries.append("{0} is \"{1}\"".format(key, value))

        query = (
            "select id from " + entitytype + " where " + " and ".join(queries)
        )
        self.log.debug(query)
        return query

    def _set_task_status(self, instance, task_entity, session):
        project_entity = instance.context.data.get("ftrackProject")
        if not project_entity:
            self.log.info("Task status won't be set, project is not known.")
            return

        if not task_entity:
            self.log.info("Task status won't be set, task is not known.")
            return

        status_name = instance.context.data.get("ftrackStatus")
        if not status_name:
            self.log.info("Ftrack status name is not set.")
            return

        self.log.debug(
            "Ftrack status name will be (maybe) set to \"{}\"".format(
                status_name
            )
        )

        project_schema = project_entity["project_schema"]
        task_statuses = project_schema.get_statuses(
            "Task", task_entity["type_id"]
        )
        task_statuses_by_low_name = {
            status["name"].lower(): status for status in task_statuses
        }
        status = task_statuses_by_low_name.get(status_name.lower())
        if not status:
            self.log.warning((
                "Task status \"{}\" won't be set,"
                " status is now allowed on task type \"{}\"."
            ).format(status_name, task_entity["type"]["name"]))
            return

        self.log.info("Setting task status to \"{}\"".format(status_name))
        task_entity["status"] = status
        try:
            session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            session.rollback()
            session._configure_locations()
            six.reraise(tp, value, tb)

    def process(self, instance):
        session = instance.context.data["ftrackSession"]
        context = instance.context

        name = None
        # If instance has set "ftrackEntity" or "ftrackTask" then use them from
        #   instance. Even if they are set to None. If they are set to None it
        #   has a reason. (like has different context)
        if "ftrackEntity" in instance.data or "ftrackTask" in instance.data:
            task = instance.data.get("ftrackTask")
            parent = instance.data.get("ftrackEntity")

        elif "ftrackEntity" in context.data or "ftrackTask" in context.data:
            task = context.data.get("ftrackTask")
            parent = context.data.get("ftrackEntity")

        if task:
            parent = task["parent"]
            name = task
        elif parent:
            name = parent["name"]

        if not name:
            self.log.info((
                "Skipping ftrack integration. Instance \"{}\" does not"
                " have specified ftrack entities."
            ).format(str(instance)))
            return

        info_msg = (
            "Created new {entity_type} with data: {data}"
            ", metadata: {metadata}."
        )

        used_asset_versions = []

        self._set_task_status(instance, task, session)

        # Iterate over components and publish
        for data in instance.data.get("ftrackComponentsList", []):
            # AssetType
            # Get existing entity.
            assettype_data = {"short": "upload"}
            assettype_data.update(data.get("assettype_data", {}))
            self.log.debug("data: {}".format(data))

            assettype_entity = session.query(
                self.query("AssetType", assettype_data)
            ).first()

            # Create a new entity if none exits.
            if not assettype_entity:
                assettype_entity = session.create("AssetType", assettype_data)
                self.log.debug("Created new AssetType with data: {}".format(
                    assettype_data
                ))

            # Asset
            # Get existing entity.
            asset_data = {
                "name": name,
                "type": assettype_entity,
                "parent": parent,
            }
            asset_data.update(data.get("asset_data", {}))

            asset_entity = session.query(
                self.query("Asset", asset_data)
            ).first()

            self.log.info("asset entity: {}".format(asset_entity))

            # Extracting metadata, and adding after entity creation. This is
            # due to a ftrack_api bug where you can't add metadata on creation.
            asset_metadata = asset_data.pop("metadata", {})

            # Create a new entity if none exits.
            if not asset_entity:
                asset_entity = session.create("Asset", asset_data)
                self.log.debug(
                    info_msg.format(
                        entity_type="Asset",
                        data=asset_data,
                        metadata=asset_metadata
                    )
                )
                try:
                    session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    session.rollback()
                    session._configure_locations()
                    six.reraise(tp, value, tb)

            # Adding metadata
            existing_asset_metadata = asset_entity["metadata"]
            existing_asset_metadata.update(asset_metadata)
            asset_entity["metadata"] = existing_asset_metadata

            # AssetVersion
            # Get existing entity.
            assetversion_data = {
                "version": 0,
                "asset": asset_entity,
            }
            _assetversion_data = data.get("assetversion_data", {})
            assetversion_cust_attrs = _assetversion_data.pop(
                "custom_attributes", {}
            )
            asset_version_comment = _assetversion_data.pop(
                "comment", None
            )
            assetversion_data.update(_assetversion_data)

            assetversion_entity = session.query(
                self.query("AssetVersion", assetversion_data)
            ).first()

            # Extracting metadata, and adding after entity creation. This is
            # due to a ftrack_api bug where you can't add metadata on creation.
            assetversion_metadata = assetversion_data.pop("metadata", {})

            if task:
                assetversion_data['task'] = task

            # Create a new entity if none exits.
            if not assetversion_entity:
                assetversion_entity = session.create(
                    "AssetVersion", assetversion_data
                )
                self.log.debug(
                    info_msg.format(
                        entity_type="AssetVersion",
                        data=assetversion_data,
                        metadata=assetversion_metadata
                    )
                )
                try:
                    session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    session.rollback()
                    session._configure_locations()
                    six.reraise(tp, value, tb)

            # Adding metadata
            existing_assetversion_metadata = assetversion_entity["metadata"]
            existing_assetversion_metadata.update(assetversion_metadata)
            assetversion_entity["metadata"] = existing_assetversion_metadata

            # Add comment
            if asset_version_comment:
                assetversion_entity["comment"] = asset_version_comment
                try:
                    session.commit()
                except Exception:
                    session.rollback()
                    session._configure_locations()
                    self.log.warning((
                        "Comment was not possible to set for AssetVersion"
                        "\"{0}\". Can't set it's value to: \"{1}\""
                    ).format(
                        assetversion_entity["id"], str(asset_version_comment)
                    ))

            # Adding Custom Attributes
            for attr, val in assetversion_cust_attrs.items():
                if attr in assetversion_entity["custom_attributes"]:
                    try:
                        assetversion_entity["custom_attributes"][attr] = val
                        session.commit()
                        continue
                    except Exception:
                        session.rollback()
                        session._configure_locations()

                self.log.warning((
                    "Custom Attrubute \"{0}\""
                    " is not available for AssetVersion <{1}>."
                    " Can't set it's value to: \"{2}\""
                ).format(attr, assetversion_entity["id"], str(val)))

            # Have to commit the version and asset, because location can't
            # determine the final location without.
            try:
                session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                session._configure_locations()
                six.reraise(tp, value, tb)

            # Component
            # Get existing entity.
            component_data = {
                "name": "main",
                "version": assetversion_entity
            }
            component_data.update(data.get("component_data", {}))

            component_entity = session.query(
                self.query("Component", component_data)
            ).first()

            component_overwrite = data.get("component_overwrite", False)
            location = data.get("component_location", session.pick_location())

            # Overwrite existing component data if requested.
            if component_entity and component_overwrite:

                origin_location = session.query(
                    "Location where name is \"ftrack.origin\""
                ).one()

                # Removing existing members from location
                components = list(component_entity.get("members", []))
                components += [component_entity]
                for component in components:
                    for loc in component["component_locations"]:
                        if location["id"] == loc["location_id"]:
                            location.remove_component(
                                component, recursive=False
                            )

                # Deleting existing members on component entity
                for member in component_entity.get("members", []):
                    session.delete(member)
                    del(member)

                try:
                    session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    session.rollback()
                    session._configure_locations()
                    six.reraise(tp, value, tb)

                # Reset members in memory
                if "members" in component_entity.keys():
                    component_entity["members"] = []

                # Add components to origin location
                try:
                    collection = clique.parse(data["component_path"])
                except ValueError:
                    # Assume its a single file
                    # Changing file type
                    name, ext = os.path.splitext(data["component_path"])
                    component_entity["file_type"] = ext

                    origin_location.add_component(
                        component_entity, data["component_path"]
                    )
                else:
                    # Changing file type
                    component_entity["file_type"] = collection.format("{tail}")

                    # Create member components for sequence.
                    for member_path in collection:

                        size = 0
                        try:
                            size = os.path.getsize(member_path)
                        except OSError:
                            pass

                        name = collection.match(member_path).group("index")

                        member_data = {
                            "name": name,
                            "container": component_entity,
                            "size": size,
                            "file_type": os.path.splitext(member_path)[-1]
                        }

                        component = session.create(
                            "FileComponent", member_data
                        )
                        origin_location.add_component(
                            component, member_path, recursive=False
                        )
                        component_entity["members"].append(component)

                # Add components to location.
                location.add_component(
                    component_entity, origin_location, recursive=True
                )

                data["component"] = component_entity
                msg = "Overwriting Component with path: {0}, data: {1}, "
                msg += "location: {2}"
                self.log.info(
                    msg.format(
                        data["component_path"],
                        component_data,
                        location
                    )
                )

            # Extracting metadata, and adding after entity creation. This is
            # due to a ftrack_api bug where you can't add metadata on creation.
            component_metadata = component_data.pop("metadata", {})

            # Create new component if none exists.
            new_component = False
            if not component_entity:
                component_entity = assetversion_entity.create_component(
                    data["component_path"],
                    data=component_data,
                    location=location
                )
                data["component"] = component_entity
                msg = "Created new Component with path: {0}, data: {1}"
                msg += ", metadata: {2}, location: {3}"
                self.log.info(
                    msg.format(
                        data["component_path"],
                        component_data,
                        component_metadata,
                        location
                    )
                )
                new_component = True

            # Adding metadata
            existing_component_metadata = component_entity["metadata"]
            existing_component_metadata.update(component_metadata)
            component_entity["metadata"] = existing_component_metadata

            # if component_data['name'] = 'ftrackreview-mp4-mp4':
            #     assetversion_entity["thumbnail_id"]

            # Setting assetversion thumbnail
            if data.get("thumbnail", False):
                assetversion_entity["thumbnail_id"] = component_entity["id"]

            # Inform user about no changes to the database.
            if (component_entity and not component_overwrite and
                    not new_component):
                data["component"] = component_entity
                self.log.info(
                    "Found existing component, and no request to overwrite. "
                    "Nothing has been changed."
                )
            else:
                # Commit changes.
                try:
                    session.commit()
                except Exception:
                    tp, value, tb = sys.exc_info()
                    session.rollback()
                    session._configure_locations()
                    six.reraise(tp, value, tb)

            if assetversion_entity not in used_asset_versions:
                used_asset_versions.append(assetversion_entity)

        asset_versions_key = "ftrackIntegratedAssetVersions"
        if asset_versions_key not in instance.data:
            instance.data[asset_versions_key] = []

        for asset_version in used_asset_versions:
            if asset_version not in instance.data[asset_versions_key]:
                instance.data[asset_versions_key].append(asset_version)

    def _ensure_asset_types_exists(self, session, component_list):
        """Make sure that all AssetType entities exists for integration.

        Returns:
            dict: All asset types by short name.
        """
        # Query existing asset types
        asset_types = session.query("select id, short from AssetType").all()
        # Stpore all existing short names
        asset_type_shorts = {asset_type["short"] for asset_type in asset_types}
        # Check which asset types are missing and store them
        asset_type_names_by_missing_shorts = {}
        default_short_name = "upload"
        for data in component_list:
            asset_type_data = data.get("assettype_data") or {}
            asset_type_short = asset_type_data.get("short")
            if not asset_type_short:
                # Use default asset type name if not set and change the
                #   input data
                asset_type_short = default_short_name
                asset_type_data["short"] = asset_type_short
                data["assettype_data"] = asset_type_data

            if (
                # Skip if short name exists
                asset_type_short in asset_type_shorts
                # Skip if short name was already added to missing types
                #   and asset type name is filled
                # - if asset type name is missing then try use name from other
                #   data
                or asset_type_names_by_missing_shorts.get(asset_type_short)
            ):
                continue

            asset_type_names_by_missing_shorts[asset_type_short] = (
                asset_type_data.get("name")
            )

        # Create missing asset types if there are any
        if asset_type_names_by_missing_shorts:
            self.log.info("Creating asset types with short names: {}".format(
                ", ".join(asset_type_names_by_missing_shorts.keys())
            ))
            for missing_short, type_name in asset_type_names_by_missing_shorts:
                # Use short for name if name is not defined
                if not type_name:
                    type_name = missing_short
                # Use short name also for name
                #   - there is not other source for 'name'
                session.create(
                    "AssetType",
                    {
                        "short": missing_short,
                        "name": type_name
                    }
                )

            # Commit creation
            session.commit()
            # Requery asset types
            asset_types = session.query(
                "select id, short from AssetType"
            ).all()

        return {asset_type["short"]: asset_type for asset_type in asset_types}

    def _ensure_asset_exists(
        self, session, asset_data, asset_type_id, parent_id
    ):
        asset_name = asset_data["name"]
        asset_entity = self._query_asset(
            session, asset_name, asset_type_id, parent_id
        )
        if asset_entity is not None:
            return asset_entity

        asset_data = {
            "name": asset_name,
            "type_id": asset_type_id,
            "context_id": parent_id
        }
        self.log.info("Created new Asset with data: {}.".format(asset_data))
        session.create("Asset", asset_data)
        session.commit()
        return self._query_asset(session, asset_name, asset_type_id, parent_id)

    def _query_asset(self, session, asset_name, asset_type_id, parent_id):
        return session.query(
            (
                "select id from Asset"
                " where name is \"{}\""
                " and type_id is \"{}\""
                " and context_id is \"{}\""
            ).format(asset_name, asset_type_id, parent_id)
        ).first()

    def _ensure_asset_version_exists(
        self, session, asset_version_data, asset_id, task_entity
    ):
        task_id = None
        if task_entity:
            task_id = task_entity["id"]

        # Try query asset version by criteria (asset id and version)
        version = asset_version_data.get("version") or 0
        asset_version_entity = self._query_asset_version(
            session, version, asset_id
        )

        # Prepare comment value
        comment = asset_version_data.get("comment") or ""
        if asset_version_entity is not None:
            changed = False
            if comment != asset_version_entity["comment"]:
                asset_version_entity["comment"] = comment
                changed = True

            if task_id != asset_version_entity["task_id"]:
                asset_version_entity["task_id"] = task_id
                changed = True

            if changed:
                session.commit()

        else:
            new_asset_version_data = {
                "version": version,
                "asset_id": asset_id
            }
            if task_id:
                new_asset_version_data["task_id"] = task_id

            if comment:
                new_asset_version_data["comment"] = comment

            self.log.info("Created new AssetVersion with data {}".format(
                new_asset_version_data
            ))
            session.create("AssetVersion", new_asset_version_data)
            session.commit()
            asset_version_entity = self._query_asset_version(
                session, version, asset_id
            )

        # Set custom attributes if there were any set
        custom_attrs = asset_version_data.get("custom_attributes") or {}
        for attr_key, attr_value in custom_attrs.items():
            if attr_key in asset_version_entity["custom_attributes"]:
                try:
                    asset_version_entity["custom_attributes"][attr_key] = (
                        attr_value
                    )
                    session.commit()
                    continue
                except Exception:
                    session.rollback()
                    session._configure_locations()

            self.log.warning(
                (
                    "Custom Attrubute \"{0}\" is not available for"
                    " AssetVersion <{1}>. Can't set it's value to: \"{2}\""
                ).format(
                    attr_key, asset_version_entity["id"], str(attr_value)
                )
            )

        return asset_version_entity

    def _query_asset_version(self, session, version, asset_id):
        return session.query(
            (
                "select id, task_id, comment from AssetVersion"
                " where version is \"{}\" and asset_id is \"{}\""
            ).format(version, asset_id)
        ).first()

    def create_component(self, session, asset_version_entity, data):
        component_data = data.get("component_data") or {}

        if not component_data.get("name"):
            component_data["name"] = "main"

        version_id = asset_version_entity["id"]
        component_data["version_id"] = version_id
        component_entity = session.query(
            (
                "select id, name from Component where name is \"{}\""
                " and version_id is \"{}\""
            ).format(component_data["name"], version_id)
        ).first()

        component_overwrite = data.get("component_overwrite", False)
        location = data.get("component_location", session.pick_location())

        # Overwrite existing component data if requested.
        if component_entity and component_overwrite:
            origin_location = session.query(
                "Location where name is \"ftrack.origin\""
            ).one()

            # Removing existing members from location
            components = list(component_entity.get("members", []))
            components += [component_entity]
            for component in components:
                for loc in component["component_locations"]:
                    if location["id"] == loc["location_id"]:
                        location.remove_component(
                            component, recursive=False
                        )

            # Deleting existing members on component entity
            for member in component_entity.get("members", []):
                session.delete(member)
                del(member)

            try:
                session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                session._configure_locations()
                six.reraise(tp, value, tb)

            # Reset members in memory
            if "members" in component_entity.keys():
                component_entity["members"] = []

            # Add components to origin location
            try:
                collection = clique.parse(data["component_path"])
            except ValueError:
                # Assume its a single file
                # Changing file type
                name, ext = os.path.splitext(data["component_path"])
                component_entity["file_type"] = ext

                origin_location.add_component(
                    component_entity, data["component_path"]
                )
            else:
                # Changing file type
                component_entity["file_type"] = collection.format("{tail}")

                # Create member components for sequence.
                for member_path in collection:

                    size = 0
                    try:
                        size = os.path.getsize(member_path)
                    except OSError:
                        pass

                    name = collection.match(member_path).group("index")

                    member_data = {
                        "name": name,
                        "container": component_entity,
                        "size": size,
                        "file_type": os.path.splitext(member_path)[-1]
                    }

                    component = session.create(
                        "FileComponent", member_data
                    )
                    origin_location.add_component(
                        component, member_path, recursive=False
                    )
                    component_entity["members"].append(component)

            # Add components to location.
            location.add_component(
                component_entity, origin_location, recursive=True
            )

            data["component"] = component_entity
            self.log.info(
                (
                    "Overwriting Component with path: {0}, data: {1},"
                    " location: {2}"
                ).format(
                    data["component_path"],
                    component_data,
                    location
                )
            )

        # Extracting metadata, and adding after entity creation. This is
        # due to a ftrack_api bug where you can't add metadata on creation.
        component_metadata = component_data.pop("metadata", {})

        # Create new component if none exists.
        new_component = False
        if not component_entity:
            component_entity = asset_version_entity.create_component(
                data["component_path"],
                data=component_data,
                location=location
            )
            data["component"] = component_entity
            self.log.info(
                (
                    "Created new Component with path: {0}, data: {1},"
                    " metadata: {2}, location: {3}"
                ).format(
                    data["component_path"],
                    component_data,
                    component_metadata,
                    location
                )
            )
            new_component = True

        # Adding metadata
        existing_component_metadata = component_entity["metadata"]
        existing_component_metadata.update(component_metadata)
        component_entity["metadata"] = existing_component_metadata

        # if component_data['name'] = 'ftrackreview-mp4-mp4':
        #     assetversion_entity["thumbnail_id"]

        # Setting assetversion thumbnail
        if data.get("thumbnail"):
            asset_version_entity["thumbnail_id"] = component_entity["id"]

        # Inform user about no changes to the database.
        if (
            component_entity
            and not component_overwrite
            and not new_component
        ):
            data["component"] = component_entity
            self.log.info(
                "Found existing component, and no request to overwrite. "
                "Nothing has been changed."
            )
        else:
            # Commit changes.
            try:
                session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                session._configure_locations()
                six.reraise(tp, value, tb)
