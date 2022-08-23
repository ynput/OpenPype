# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import warnings

import ftrack_api.entity.base


class Note(ftrack_api.entity.base.Entity):
    '''Represent a note.'''

    def create_reply(
        self, content, author
    ):
        '''Create a reply with *content* and *author*.

        .. note::

            This is a helper method. To create replies manually use the
            standard :meth:`Session.create` method.

        '''
        reply = self.session.create(
            'Note', {
                'author': author,
                'content': content
            }
        )

        self['replies'].append(reply)

        return reply


class CreateNoteMixin(object):
    '''Mixin to add create_note method on entity class.'''

    def create_note(
        self, content, author, recipients=None, category=None, labels=None
    ):
        '''Create note with *content*, *author*.

        NoteLabels can be set by including *labels*.

        Note category can be set by including *category*.
        
        *recipients* can be specified as a list of user or group instances.

        '''
        note_label_support = 'NoteLabel' in self.session.types

        if not labels:
            labels = []

        if labels and not note_label_support:
            raise ValueError(
                'NoteLabel is not supported by the current server version.'
            )

        if category and labels:
            raise ValueError(
                'Both category and labels cannot be set at the same time.'
            )

        if not recipients:
            recipients = []

        data = {
            'content': content,
            'author': author
        }

        if category:
            if note_label_support:
                labels = [category]
                warnings.warn(
                    'category argument will be removed in an upcoming version, '
                    'please use labels instead.',
                    PendingDeprecationWarning
                )
            else:
                data['category_id'] = category['id']

        note = self.session.create('Note', data)

        self['notes'].append(note)

        for resource in recipients:
            recipient = self.session.create('Recipient', {
                'note_id': note['id'],
                'resource_id': resource['id']
            })

            note['recipients'].append(recipient)

        for label in labels:
            self.session.create(
                'NoteLabelLink',
                {
                    'label_id': label['id'],
                    'note_id': note['id']
                }
            )

        return note
