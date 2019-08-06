import os
from pype.vendor import ftrack_api
from pype.ftrack import BaseAction
from pype.vendor.ftrack_api import session as fa_session


class ActionAskWhereIRun(BaseAction):
    """ Sometimes user forget where pipeline with his credentials is running.
    - this action triggers `ActionShowWhereIRun`
    """
    # Action is ignored by default
    ignore_me = True
    #: Action identifier.
    identifier = 'ask.where.i.run'
    #: Action label.
    label = 'Ask where I run'
    #: Action description.
    description = 'Triggers PC info where user have running Pype'
    #: Action icon
    icon = '{}/ftrack/action_icons/ActionAskWhereIRun.svg'.format(
        os.environ.get('PYPE_STATICS_SERVER', '')
    )

    def discover(self, session, entities, event):
        """ Hide by default - Should be enabled only if you want to run.
        - best practise is to create another action that triggers this one
        """

        return True

    def launch(self, session, entities, event):
        event = fa_session.ftrack_api.event.base.Event(
            topic='ftrack.action.launch',
            data=dict(
                actionIdentifier="show.where.i.run",
                selection=event["data"]["selection"],
                event_hub_id=session.event_hub.id
            ),
            source=dict(
                user=dict(username=session.api_user)
            )
        )
        session.event_hub.publish(event, on_error='ignore')

        return True


def register(session, **kw):
    '''Register plugin. Called when used as an plugin.'''

    if not isinstance(session, ftrack_api.session.Session):
        return

    ActionAskWhereIRun(session).register()
