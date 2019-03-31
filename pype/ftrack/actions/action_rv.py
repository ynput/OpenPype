from pype.ftrack import BaseAction
import os
import sys
import json
try:
    import ftrack
except ImportError:
    dependencies_path = os.path.abspath(
        os.path.join(os.environ.get('PYPE_STUDIO_CONFIG'),
                     'pype', 'vendor', 'ftrack_legacy'))

    sys.path.append(dependencies_path)
    import ftrack


class RVAction(BaseAction):
    """ Launch RV action """
    identifier = "rv-launch-action"
    label = "rv"
    description = "rv Launcher"
    icon = "https://img.icons8.com/color/48/000000/circled-play.png"

    def _createPlaylistFromSelection(self, selection):
        '''Return new selection with temporary playlist from *selection*.'''

        # If selection is only one entity we don't need to create
        # a playlist.
        if len(selection) == 1:
            return selection

        playlist = []
        for entity in selection:
            playlist.append({
                'id': entity['entityId'],
                'type': entity['entityType']
            })

        playlist = ftrack.createTempData(json.dumps(playlist))

        selection = [{
            'entityType': 'tempdata',
            'entityId': playlist.getId()
        }]

        return selection

    def discover(self, session, entities, event):
        """Return available actions based on *event*. """
        selection = event["data"].get("selection", [])
        if len(selection) != 1:
            return False

        entityType = selection[0].get("entityType", None)
        if entityType in ["assetversion", "task"]:
            return True
        return False

    def launch(self, session, entities, event):
        pass

    def register(session, **kw):
        super().register()


def main(arguments=None):
    pass


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
