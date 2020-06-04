from pype.modules.ftrack.lib import BaseAction, statics_icon


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
    icon = statics_icon("ftrack", "action_icons", "ActionAskWhereIRun.svg")

    def discover(self, session, entities, event):
        """ Hide by default - Should be enabled only if you want to run.
        - best practise is to create another action that triggers this one
        """

        return True

    def launch(self, session, entities, event):
        more_data = {"event_hub_id": session.event_hub.id}
        self.trigger_action(
            "show.where.i.run", event, additional_event_data=more_data
        )

        return True


def register(session, plugins_presets={}):
    '''Register plugin. Called when used as an plugin.'''

    ActionAskWhereIRun(session, plugins_presets).register()
