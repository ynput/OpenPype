# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api.entity.base


class Component(ftrack_api.entity.base.Entity):
    '''Represent a component.'''

    def get_availability(self, locations=None):
        '''Return availability in *locations*.

        If *locations* is None, all known locations will be checked.

        Return a dictionary of {location_id:percentage_availability}

        '''
        return self.session.get_component_availability(
            self, locations=locations
        )


class CreateThumbnailMixin(object):
    '''Mixin to add create_thumbnail method on entity class.'''

    def create_thumbnail(self, path, data=None):
        '''Set entity thumbnail from *path*.

        Creates a thumbnail component using in the ftrack.server location 
        :meth:`Session.create_component 
        <ftrack_api.session.Session.create_component>` The thumbnail component
        will be created using *data* if specified. If no component name is
        given, `thumbnail` will be used.

        The file is expected to be of an appropriate size and valid file
        type.

        .. note::

            A :meth:`Session.commit<ftrack_api.session.Session.commit>` will be
            automatically issued.

        '''
        if data is None:
            data = {}
        if not data.get('name'):
            data['name'] = 'thumbnail'

        thumbnail_component = self.session.create_component(
            path, data, location=None
        )

        origin_location = self.session.get(
            'Location', ftrack_api.symbol.ORIGIN_LOCATION_ID
        )
        server_location = self.session.get(
            'Location', ftrack_api.symbol.SERVER_LOCATION_ID
        )
        server_location.add_component(thumbnail_component, [origin_location])

        # TODO: This commit can be avoided by reordering the operations in 
        # this method so that the component is transferred to ftrack.server
        # after the thumbnail has been set.
        # 
        # There is currently a bug in the API backend, causing the operations
        # to *some* times be ordered wrongly, where the update occurs before
        # the component has been created, causing an integrity error.
        # 
        # Once this issue has been resolved, this commit can be removed and
        # and the update placed between component creation and registration. 
        self['thumbnail_id'] = thumbnail_component['id']
        self.session.commit()

        return thumbnail_component
