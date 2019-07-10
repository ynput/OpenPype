import os
import sys
import argparse
import json
import logging
import collections
import tempfile
import requests

from pype.vendor import ftrack_api
from pype.ftrack import BaseAction
from pypeapp import config


class SyncAssetVersions(BaseAction):

    #: Action identifier.
    identifier = 'sync.asset.versions'
    #: Action label.
    label = 'Sync Asset Versions'
    #: Action description.
    description = 'Synchronize Asset versions to another Ftrack'
    #: roles that are allowed to register this action
    role_list = ['Administrator', 'Project Manager', 'Pypeclub']

    # ENTER VALUES HERE (change values based on keys)
    # Custom attribute storing ftrack id of destination server
    id_key_src = 'fridge_ftrackID'
    # Custom attribute storing ftrack id of source server
    id_key_dst = 'kredenc_ftrackID'

    components_name = (
        'ftrackreview-mp4_src',
        'ftrackreview-image_src',
        'thumbnail_src'
    )

    # comp name mapping
    comp_name_mapping = {
        'ftrackreview-mp4_src': 'ftrackreview-mp4',
        'ftrackreview-image_src': 'ftrackreview-image',
        'thumbnail_src': 'thumbnail'
    }

    comp_location_mapping = {
        'ftrack.server': [
            'ftrackreview-mp4',
            'ftrackreview-mp4_src',
            'ftrackreview-image',
            'ftrackreview-image_src',
            'thumbnail',
            'thumbnail_src'
        ],
        'ftrack.unmanaged': []
    }

    def discover(self, session, entities, event):
        ''' Validation '''
        for entity in entities:
            if entity.entity_type.lower() != 'assetversion':
                return False

        return True

    def launch(self, session, entities, event):
        self.dst_ftrack_locations = {}
        self.interface_messages = {}
        # stop if custom attribute for storing second ftrack id is missing
        if self.id_key_src not in entities[0]['custom_attributes']:
            msg = (
                'Custom attribute "{}" does not exist on AssetVersion'
            ).format(self.id_key_src)
            self.log.error(msg)

            return {
                'success': False,
                'message': msg
            }

        source_credentials = config.get_presets()['ftrack'].get(
            'partnership_ftrack_cred', {}
        )
        self.dst_session = ftrack_api.Session(
            server_url=source_credentials.get('server_url'),
            api_key=source_credentials.get('api_key'),
            api_user=source_credentials.get('api_user'),
            auto_connect_event_hub=True
        )

        # NOTE Shared session has issues with location definition
        self.session_for_components = ftrack_api.Session(
            server_url=session.server_url,
            api_key=session.api_key,
            api_user=session.api_user,
            auto_connect_event_hub=True
        )

        for entity in entities:
            asset = entity['asset']
            parent = asset['parent']

            # Check if asset version already has entity on destinaition Ftrack
            # TODO  ? skip if yes
            #       ? show to user - with interface/message/note
            #       + or ask if user want to override found version ????
            dst_ftrack_id = entity['custom_attributes'].get(self.id_key_src)
            if dst_ftrack_id:
                dst_ftrack_ent = self.dst_session.query(
                    'AssetVersion where id = "{}"'.format(dst_ftrack_id)
                ).first()

                if dst_ftrack_ent:
                    self.log.warning(
                        '"{}" - Already exists. Skipping'.format(asset['name'])
                    )
                    continue

            # Find parent where Version will be uploaded
            dst_parent_id = parent['custom_attributes'].get(self.id_key_src)
            if not dst_parent_id:
                self.log.warning((
                    'Entity: "{}" don\'t have stored Custom attribute "{}"'
                ).format(parent['name'], self.id_key_src))
                continue

            dst_parent_entity = self.dst_session.query(
                'TypedContext where id = "{}"'.format(dst_parent_id)
            ).first()

            if not dst_parent_entity:
                msg = (
                    'Didn\'t found mirrored entity in destination Ftrack'
                    ' for "{}"'
                ).format(parent['name'])
                self.log.warning(msg)
                continue

            component_list = self.prepare_data(entity['id'])
            id_stored = False
            for comp_data in component_list:
                dst_asset_ver_id = self.asset_version_creation(
                    dst_parent_entity, comp_data, entity
                )

                if id_stored:
                    continue
                entity['custom_attributes'][self.id_key_src] = dst_asset_ver_id
                session.commit()
                id_stored = True

        self.dst_session.close()
        self.session_for_components.close()

        self.dst_session = None
        self.session_for_components = None

        return True

    def prepare_data(self, asset_version_id):
        components_list = []
        asset_version = self.session_for_components.query(
            'AssetVersion where id is "{}"'.format(asset_version_id)
        ).one()
        # Asset data
        asset_type = asset_version['asset']['type'].get('short', 'upload')
        assettype_data = {'short': asset_type}

        asset_data = {'name': asset_version['asset']['name']}

        # Asset version data
        assetversion_data = {'version': asset_version['version']}

        # Component data
        components_of_interest = {}
        for name in self.components_name:
            components_of_interest[name] = False

        for key in components_of_interest:
            # Find component by name
            for comp in asset_version['components']:
                if comp['name'] == key:
                    components_of_interest[key] = True
                    break
            # NOTE if component was found then continue
            if components_of_interest[key]:
                continue

            # Look for alternative component name set in mapping
            new_key = None
            if key in self.comp_name_mapping:
                new_key = self.comp_name_mapping[key]

            if not new_key:
                self.log.warning(
                    'Asset version do not have components "{}" or "{}"'.format(
                        key, new_key
                    )
                )
                continue

            components_of_interest[new_key] = components_of_interest.pop(key)

            # Try to look for alternative name
            for comp in asset_version['components']:
                if comp['name'] == new_key:
                    components_of_interest[new_key] = True
                    break

        # Check if at least one component is transferable
        have_comp_to_transfer = False
        for value in components_of_interest.values():
            if value:
                have_comp_to_transfer = True
                break

        if not have_comp_to_transfer:
            return components_list

        thumbnail_id = asset_version.get('thumbnail_id')
        temp_folder = tempfile.mkdtemp('components')

        # Data for transfer components
        for comp in asset_version['components']:
            comp_name = comp['name']

            if comp_name not in components_of_interest:
                continue

            if not components_of_interest[comp_name]:
                continue

            if comp_name in self.comp_name_mapping:
                comp_name = self.comp_name_mapping[comp_name]

            is_thumbnail = False
            for _comp in asset_version['components']:
                if _comp['name'] == comp_name:
                    if _comp['id'] == thumbnail_id:
                        is_thumbnail = True
                    break

            locatiom_name = comp['component_locations'][0]['location']['name']
            location = self.session_for_components.query(
                'Location where name is "{}"'.format(locatiom_name)
            ).one()
            file_path = None
            if locatiom_name == 'ftrack.unmanaged':
                file_path = ''
                try:
                    file_path = location.get_filesystem_path(comp)
                except Exception:
                    pass

                file_path = os.path.normpath(file_path)
                if not os.path.exists(file_path):
                    file_path = comp['component_locations'][0][
                        'resource_identifier'
                    ]

                file_path = os.path.normpath(file_path)
                if not os.path.exists(file_path):
                    self.log.warning(
                        'In component: "{}" can\'t access filepath: "{}"'.format(
                            comp['name'], file_path
                        )
                    )
                    continue

            elif locatiom_name == 'ftrack.server':
                download_url = location.get_url(comp)

                file_name = '{}{}{}'.format(
                    asset_version['asset']['name'],
                    comp_name,
                    comp['file_type']
                )
                file_path = os.path.sep.join([temp_folder, file_name])

                self.download_file(download_url, file_path)

            if not file_path:
                self.log.warning(
                    'In component: "{}" is invalid file path'.format(
                        comp['name']
                    )
                )
                continue

            # Default location name value is ftrack.unmanaged
            location_name = 'ftrack.unmanaged'

            # Try to find location where component will be created
            for name, keys in self.comp_location_mapping.items():
                if comp_name in keys:
                    location_name = name
                    break
            dst_location = self.get_dst_location(location_name)

            # Metadata
            metadata = {}
            metadata.update(comp.get('metadata', {}))

            component_data = {
                "name": comp_name,
                "metadata": metadata
            }

            data = {
                'assettype_data': assettype_data,
                'asset_data': asset_data,
                'assetversion_data': assetversion_data,
                'component_data': component_data,
                'component_overwrite': False,
                'thumbnail': is_thumbnail,
                'component_location': dst_location,
                'component_path': file_path
            }

            components_list.append(data)

        return components_list

    def asset_version_creation(self, dst_parent_entity, data, src_entity):
        assettype_data = data['assettype_data']
        self.log.debug("data: {}".format(data))

        assettype_entity = self.dst_session.query(
            self.query("AssetType", assettype_data)
        ).first()

        # Create a new entity if none exits.
        if not assettype_entity:
            assettype_entity = self.dst_session.create(
                "AssetType", assettype_data
            )
            self.dst_session.commit()
            self.log.debug(
                "Created new AssetType with data: ".format(assettype_data)
            )

        # Asset
        # Get existing entity.
        asset_data = {
            "name": src_entity['asset']['name'],
            "type": assettype_entity,
            "parent": dst_parent_entity
        }
        asset_data.update(data.get("asset_data", {}))

        asset_entity = self.dst_session.query(
            self.query("Asset", asset_data)
        ).first()

        self.log.info("asset entity: {}".format(asset_entity))

        # Extracting metadata, and adding after entity creation. This is
        # due to a ftrack_api bug where you can't add metadata on creation.
        asset_metadata = asset_data.pop("metadata", {})

        # Create a new entity if none exits.
        info_msg = (
            'Created new {entity_type} with data: {data}'
            ", metadata: {metadata}."
        )

        if not asset_entity:
            asset_entity = self.dst_session.create("Asset", asset_data)
            self.dst_session.commit()

            self.log.debug(
                info_msg.format(
                    entity_type="Asset",
                    data=asset_data,
                    metadata=asset_metadata
                )
            )

        # Adding metadata
        existing_asset_metadata = asset_entity["metadata"]
        existing_asset_metadata.update(asset_metadata)
        asset_entity["metadata"] = existing_asset_metadata

        # AssetVersion
        assetversion_data = {
            'version': 0,
            'asset': asset_entity
        }

        # NOTE task is skipped (can't be identified in other ftrack)
        # if task:
        #     assetversion_data['task'] = task

        # NOTE assetversion_data contains version number which is not correct
        assetversion_data.update(data.get("assetversion_data", {}))

        assetversion_entity = self.dst_session.query(
            self.query("AssetVersion", assetversion_data)
        ).first()

        # Extracting metadata, and adding after entity creation. This is
        # due to a ftrack_api bug where you can't add metadata on creation.
        assetversion_metadata = assetversion_data.pop("metadata", {})

        # Create a new entity if none exits.
        if not assetversion_entity:
            assetversion_entity = self.dst_session.create(
                "AssetVersion", assetversion_data
            )
            self.dst_session.commit()

            self.log.debug(
                info_msg.format(
                    entity_type="AssetVersion",
                    data=assetversion_data,
                    metadata=assetversion_metadata
                )
            )

        # Check if custom attribute can of main Ftrack can be set
        if self.id_key_dst not in assetversion_entity['custom_attributes']:
            self.log.warning((
                'Destination Asset Version do not have key "{}" in'
                ' Custom attributes'
            ).format(self.id_key_dst))
            return

        assetversion_entity['custom_attributes'][self.id_key_dst] = src_entity['id']

        # Adding metadata
        existing_assetversion_metadata = assetversion_entity["metadata"]
        existing_assetversion_metadata.update(assetversion_metadata)
        assetversion_entity["metadata"] = existing_assetversion_metadata

        # Have to commit the version and asset, because location can't
        # determine the final location without.
        self.dst_session.commit()

        # Component
        # Get existing entity.
        component_data = {
            "name": "main",
            "version": assetversion_entity
        }
        component_data.update(data.get("component_data", {}))

        component_entity = self.dst_session.query(
            self.query("Component", component_data)
        ).first()

        component_overwrite = data.get("component_overwrite", False)

        location = None
        location_name = data.get("component_location", {}).get('name')
        if location_name:
            location = self.dst_session.query(
                'Location where name is "{}"'.format(location_name)
            ).first()

        if not location:
            location = self.dst_session.pick_location()

        # Overwrite existing component data if requested.
        if component_entity and component_overwrite:

            origin_location = self.dst_session.query(
                'Location where name is "ftrack.origin"'
            ).one()

            # Removing existing members from location
            components = list(component_entity.get("members", []))
            components += [component_entity,]
            for component in components:
                for loc in component["component_locations"]:
                    if location["id"] == loc["location_id"]:
                        location.remove_component(
                            component, recursive=False
                        )

            # Deleting existing members on component entity
            for member in component_entity.get("members", []):
                self.dst_session.delete(member)
                del(member)

            self.dst_session.commit()

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

                    component = self.dst_session.create(
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
            msg = (
                "Created new Component with path: {}, data: {}"
                ", metadata: {}, location: {}"
            )
            self.log.info(msg.format(
                data["component_path"],
                component_data,
                component_metadata,
                location['name']
            ))
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
        if (
            component_entity and
            not component_overwrite and
            not new_component
        ):
            data["component"] = component_entity
            self.log.info(
                "Found existing component, and no request to overwrite. "
                "Nothing has been changed."
            )
            return

        # Commit changes.
        self.dst_session.commit()

        return assetversion_entity['id']

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
            entitytype + " where " + " and ".join(queries)
        )
        return query

    def download_file(self, url, path):
        r = requests.get(url, stream=True).content
        with open(path, 'wb') as f:
            f.write(r)

    def get_dst_location(self, name):
        if name in self.dst_ftrack_locations:
            return self.dst_ftrack_locations[name]

        location = self.dst_session.query(
            'Location where name is "{}"'.format(name)
        ).one()
        self.dst_ftrack_locations[name] = location
        return location


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    SyncAssetVersions(session).register()


def main(arguments=None):
    '''Set up logging and register action.'''
    if arguments is None:
        arguments = []

    parser = argparse.ArgumentParser()
    # Allow setting of logging level from arguments.
    loggingLevels = {}
    for level in (
        logging.NOTSET, logging.DEBUG, logging.INFO, logging.WARNING,
        logging.ERROR, logging.CRITICAL
    ):
        loggingLevels[logging.getLevelName(level).lower()] = level

    parser.add_argument(
        '-v', '--verbosity',
        help='Set the logging output verbosity.',
        choices=loggingLevels.keys(),
        default='info'
    )
    namespace = parser.parse_args(arguments)

    # Set up basic logging
    logging.basicConfig(level=loggingLevels[namespace.verbosity])

    session = ftrack_api.Session()
    register(session)

    # Wait for events
    logging.info(
        'Registered actions and listening for events. Use Ctrl-C to abort.'
    )
    session.event_hub.wait()


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
