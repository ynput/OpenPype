# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api.entity.base


class ProjectSchema(ftrack_api.entity.base.Entity):
    '''Class representing ProjectSchema.'''

    def get_statuses(self, schema, type_id=None):
        '''Return statuses for *schema* and optional *type_id*.

        *type_id* is the id of the Type for a TypedContext and can be used to
        get statuses where the workflow has been overridden.

        '''
        # Task has overrides and need to be handled separately.
        if schema == 'Task':
            if type_id is not None:
                overrides = self['_overrides']
                for override in overrides:
                    if override['type_id'] == type_id:
                        return override['workflow_schema']['statuses'][:]

            return self['_task_workflow']['statuses'][:]

        elif schema == 'AssetVersion':
            return self['_version_workflow']['statuses'][:]

        else:
            try:
                EntityTypeClass = self.session.types[schema]
            except KeyError:
                raise ValueError('Schema {0} does not exist.'.format(schema))

            object_type_id_attribute = EntityTypeClass.attributes.get(
                'object_type_id'
            )

            try:
                object_type_id = object_type_id_attribute.default_value
            except AttributeError:
                raise ValueError(
                    'Schema {0} does not have statuses.'.format(schema)
                )

            for _schema in self['_schemas']:
                if _schema['type_id'] == object_type_id:
                    result = self.session.query(
                        'select task_status from SchemaStatus '
                        'where schema_id is {0}'.format(_schema['id'])
                    )
                    return [
                        schema_type['task_status'] for schema_type in result
                    ]

            raise ValueError(
                'No valid statuses were found for schema {0}.'.format(schema)
            )

    def get_types(self, schema):
        '''Return types for *schema*.'''
        # Task need to be handled separately.
        if schema == 'Task':
            return self['_task_type_schema']['types'][:]

        else:
            try:
                EntityTypeClass = self.session.types[schema]
            except KeyError:
                raise ValueError('Schema {0} does not exist.'.format(schema))

            object_type_id_attribute = EntityTypeClass.attributes.get(
                'object_type_id'
            )

            try:
                object_type_id = object_type_id_attribute.default_value
            except AttributeError:
                raise ValueError(
                    'Schema {0} does not have types.'.format(schema)
                )

            for _schema in self['_schemas']:
                if _schema['type_id'] == object_type_id:
                    result = self.session.query(
                        'select task_type from SchemaType '
                        'where schema_id is {0}'.format(_schema['id'])
                    )
                    return [schema_type['task_type'] for schema_type in result]

            raise ValueError(
                'No valid types were found for schema {0}.'.format(schema)
            )
