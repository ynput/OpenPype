from openpype_modules.ftrack.lib import BaseAction, statics_icon
try:
    from functools import cmp_to_key
except Exception:
    cmp_to_key = None


def existence_comaprison(item_a, item_b):
    if not item_a and not item_b:
        return 0
    if not item_a:
        return 1
    if not item_b:
        return -1
    return None


def task_name_sorter(item_a, item_b):
    asset_version_a = item_a["asset_version"]
    asset_version_b = item_b["asset_version"]
    asset_version_comp = existence_comaprison(asset_version_a, asset_version_b)
    if asset_version_comp is not None:
        return asset_version_comp

    task_a = asset_version_a["task"]
    task_b = asset_version_b["task"]
    task_comp = existence_comaprison(task_a, task_b)
    if task_comp is not None:
        return task_comp

    if task_a["name"] > task_b["name"]:
        return 1
    if task_a["name"] < task_b["name"]:
        return -1
    return 0


if cmp_to_key:
    task_name_sorter = cmp_to_key(task_name_sorter)
task_name_kwarg_key = "key" if cmp_to_key else "cmp"
task_name_sort_kwargs = {task_name_kwarg_key: task_name_sorter}


class ClientReviewSort(BaseAction):
    '''Custom action.'''

    #: Action identifier.
    identifier = 'client.review.sort'

    #: Action label.
    label = 'Sort Review'

    icon = statics_icon("ftrack", "action_icons", "SortReview.svg")

    def discover(self, session, entities, event):
        ''' Validation '''

        if (len(entities) == 0 or entities[0].entity_type != 'ReviewSession'):
            return False

        return True

    def launch(self, session, entities, event):
        entity = entities[0]

        # Get all objects from Review Session and all 'sort order' possibilities
        obj_list = []
        sort_order_list = []
        for obj in entity['review_session_objects']:
            obj_list.append(obj)
            sort_order_list.append(obj['sort_order'])

        # Sort criteria
        obj_list = sorted(obj_list, key=lambda k: k['version'])
        obj_list.sort(**task_name_sort_kwargs)
        obj_list = sorted(obj_list, key=lambda k: k['name'])
        # Set 'sort order' to sorted list, so they are sorted in Ftrack also
        for i in range(len(obj_list)):
            obj_list[i]['sort_order'] = sort_order_list[i]

        session.commit()

        return {
            'success': True,
            'message': 'Client Review sorted!'
        }


def register(session):
    '''Register action. Called when used as an event plugin.'''

    ClientReviewSort(session).register()
