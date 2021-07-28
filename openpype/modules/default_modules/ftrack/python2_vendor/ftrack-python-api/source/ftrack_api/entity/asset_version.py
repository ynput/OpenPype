# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import ftrack_api.entity.base


class AssetVersion(ftrack_api.entity.base.Entity):
    '''Represent asset version.'''

    def create_component(
        self, path, data=None, location=None
    ):
        '''Create a new component from *path* with additional *data*

        .. note::

            This is a helper method. To create components manually use the
            standard :meth:`Session.create` method.

        *path* can be a string representing a filesystem path to the data to
        use for the component. The *path* can also be specified as a sequence
        string, in which case a sequence component with child components for
        each item in the sequence will be created automatically. The accepted
        format for a sequence is '{head}{padding}{tail} [{ranges}]'. For
        example::

            '/path/to/file.%04d.ext [1-5, 7, 8, 10-20]'

        .. seealso::

            `Clique documentation <http://clique.readthedocs.org>`_

        *data* should be a dictionary of any additional data to construct the
        component with (as passed to :meth:`Session.create`). This version is
        automatically set as the component's version.

        If *location* is specified then automatically add component to that
        location.

        '''
        if data is None:
            data = {}

        data.pop('version_id', None)
        data['version'] = self

        return self.session.create_component(path, data=data, location=location)

    def encode_media(self, media, keep_original='auto'):
        '''Return a new Job that encode *media* to make it playable in browsers.

        *media* can be a path to a file or a FileComponent in the ftrack.server
        location.

        The job will encode *media* based on the file type and job data contains
        information about encoding in the following format::

            {
                'output': [{
                    'format': 'video/mp4',
                    'component_id': 'e2dc0524-b576-11d3-9612-080027331d74'
                }, {
                    'format': 'image/jpeg',
                    'component_id': '07b82a97-8cf9-11e3-9383-20c9d081909b'
                }],
                'source_component_id': 'e3791a09-7e11-4792-a398-3d9d4eefc294',
                'keep_original': True
            }

        The output components are associated with the job via the job_components
        relation.

        An image component will always be generated if possible, and will be 
        set as the version's thumbnail.

        The new components will automatically be associated with the version.
        A server version of 3.3.32 or higher is required for this to function
        properly.

        If *media* is a file path, a new source component will be created and
        added to the ftrack server location and a call to :meth:`commit` will be
        issued. If *media* is a FileComponent, it will be assumed to be in
        available in the ftrack.server location.

        If *keep_original* is not set, the original media will be kept if it
        is a FileComponent, and deleted if it is a file path. You can specify
        True or False to change this behavior.
        '''
        return self.session.encode_media(
            media, version_id=self['id'], keep_original=keep_original
        )
