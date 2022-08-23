# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api.entity.factory


class CustomUser(ftrack_api.entity.base.Entity):
    '''Represent custom user.'''


def test_extend_standard_factory_with_bases(session):
    '''Successfully add extra bases to standard factory.'''
    standard_factory = ftrack_api.entity.factory.StandardFactory()

    schemas = session._load_schemas(False)
    user_schema = [
        schema for schema in schemas if schema['id'] == 'User'
    ].pop()

    user_class = standard_factory.create(user_schema, bases=[CustomUser])
    session.types[user_class.entity_type] = user_class

    user = session.query('User').first()

    assert CustomUser in type(user).__mro__
