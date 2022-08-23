# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import re
import unicodedata

import ftrack_api.symbol
import ftrack_api.structure.base


class StandardStructure(ftrack_api.structure.base.Structure):
    '''Project hierarchy based structure that only supports Components.

    The resource identifier is generated from the project code, the name
    of objects in the project structure, asset name and version number::

        my_project/folder_a/folder_b/asset_name/v003

    If the component is a `FileComponent` then the name of the component and the
    file type are used as filename in the resource_identifier::

        my_project/folder_a/folder_b/asset_name/v003/foo.jpg

    If the component is a `SequenceComponent` then a sequence expression,
    `%04d`, is used. E.g. a component with the name `foo` yields::

        my_project/folder_a/folder_b/asset_name/v003/foo.%04d.jpg

    For the member components their index in the sequence is used::

        my_project/folder_a/folder_b/asset_name/v003/foo.0042.jpg

    The name of the component is added to the resource identifier if the
    component is a `ContainerComponent`. E.g. a container component with the
    name `bar` yields::

        my_project/folder_a/folder_b/asset_name/v003/bar

    For a member of that container the file name is based on the component name
    and file type::

        my_project/folder_a/folder_b/asset_name/v003/bar/baz.pdf

    '''

    def __init__(
        self, project_versions_prefix=None, illegal_character_substitute='_'
    ):
        '''Initialise structure.

        If *project_versions_prefix* is defined, insert after the project code
        for versions published directly under the project::

            my_project/<project_versions_prefix>/v001/foo.jpg

        Replace illegal characters with *illegal_character_substitute* if
        defined.

        .. note::

            Nested component containers/sequences are not supported.

        '''
        super(StandardStructure, self).__init__()
        self.project_versions_prefix = project_versions_prefix
        self.illegal_character_substitute = illegal_character_substitute

    def _get_parts(self, entity):
        '''Return resource identifier parts from *entity*.'''
        session = entity.session

        version = entity['version']

        if version is ftrack_api.symbol.NOT_SET and entity['version_id']:
            version = session.get('AssetVersion', entity['version_id'])

        error_message = (
            'Component {0!r} must be attached to a committed '
            'version and a committed asset with a parent context.'.format(
                entity
            )
        )

        if (
            version is ftrack_api.symbol.NOT_SET or
            version in session.created
        ):
            raise ftrack_api.exception.StructureError(error_message)

        link = version['link']

        if not link:
            raise ftrack_api.exception.StructureError(error_message)

        structure_names = [
            item['name']
            for item in link[1:-1]
        ]

        project_id = link[0]['id']
        project = session.get('Project', project_id)
        asset = version['asset']

        version_number = self._format_version(version['version'])

        parts = []
        parts.append(project['name'])

        if structure_names:
            parts.extend(structure_names)
        elif self.project_versions_prefix:
            # Add *project_versions_prefix* if configured and the version is
            # published directly under the project.
            parts.append(self.project_versions_prefix)

        parts.append(asset['name'])
        parts.append(version_number)

        return [self.sanitise_for_filesystem(part) for part in parts]

    def _format_version(self, number):
        '''Return a formatted string representing version *number*.'''
        return 'v{0:03d}'.format(number)

    def sanitise_for_filesystem(self, value):
        '''Return *value* with illegal filesystem characters replaced.

        An illegal character is one that is not typically valid for filesystem
        usage, such as non ascii characters, or can be awkward to use in a
        filesystem, such as spaces. Replace these characters with
        the character specified by *illegal_character_substitute* on
        initialisation. If no character was specified as substitute then return
        *value* unmodified.

        '''
        if self.illegal_character_substitute is None:
            return value

        if isinstance(value, str):
            value = value.decode('utf-8')

        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
        value = re.sub('[^\w\.-]', self.illegal_character_substitute, value)
        return unicode(value.strip().lower())

    def get_resource_identifier(self, entity, context=None):
        '''Return a resource identifier for supplied *entity*.

        *context* can be a mapping that supplies additional information, but
        is unused in this implementation.


        Raise a :py:exc:`ftrack_api.exeption.StructureError` if *entity* is not
        attached to a committed version and a committed asset with a parent
        context.

        '''
        if entity.entity_type in ('FileComponent',):
            container = entity['container']

            if container:
                # Get resource identifier for container.
                container_path = self.get_resource_identifier(container)

                if container.entity_type in ('SequenceComponent',):
                    # Strip the sequence component expression from the parent
                    # container and back the correct filename, i.e.
                    # /sequence/component/sequence_component_name.0012.exr.
                    name = '{0}.{1}{2}'.format(
                        container['name'], entity['name'], entity['file_type']
                    )
                    parts = [
                        os.path.dirname(container_path),
                        self.sanitise_for_filesystem(name)
                    ]

                else:
                    # Container is not a sequence component so add it as a
                    # normal component inside the container.
                    name = entity['name'] + entity['file_type']
                    parts = [
                        container_path, self.sanitise_for_filesystem(name)
                    ]

            else:
                # File component does not have a container, construct name from
                # component name and file type.
                parts = self._get_parts(entity)
                name = entity['name'] + entity['file_type']
                parts.append(self.sanitise_for_filesystem(name))

        elif entity.entity_type in ('SequenceComponent',):
            # Create sequence expression for the sequence component and add it
            # to the parts.
            parts = self._get_parts(entity)
            sequence_expression = self._get_sequence_expression(entity)
            parts.append(
                '{0}.{1}{2}'.format(
                    self.sanitise_for_filesystem(entity['name']),
                    sequence_expression,
                    self.sanitise_for_filesystem(entity['file_type'])
                )
            )

        elif entity.entity_type in ('ContainerComponent',):
            # Add the name of the container to the resource identifier parts.
            parts = self._get_parts(entity)
            parts.append(self.sanitise_for_filesystem(entity['name']))

        else:
            raise NotImplementedError(
                'Cannot generate resource identifier for unsupported '
                'entity {0!r}'.format(entity)
            )

        return self.path_separator.join(parts)
