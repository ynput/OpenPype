from openpype.pipeline import create
from openpype.pipeline import CreatorError
from openpype.hosts.aftereffects.api import (
    get_stub,
    list_instances
)


class CreateRender(create.LegacyCreator):
    """Render folder for publish.

        Creates subsets in format 'familyTaskSubsetname',
        eg 'renderCompositingMain'.

        Create only single instance from composition at a time.
    """

    name = "renderDefault"
    label = "Render on Farm"
    family = "render"
    defaults = ["Main"]

    def process(self):
        stub = get_stub()  # only after After Effects is up
        if (self.options or {}).get("useSelection"):
            items = stub.get_selected_items(
                comps=True, folders=False, footages=False
            )
        if len(items) > 1:
            raise CreatorError(
                "Please select only single composition at time."
            )

        if not items:
            raise CreatorError((
                "Nothing to create. Select composition "
                "if 'useSelection' or create at least "
                "one composition."
            ))

        existing_subsets = [
            instance['subset'].lower()
            for instance in list_instances()
        ]

        item = items.pop()
        if self.name.lower() in existing_subsets:
            txt = "Instance with name \"{}\" already exists.".format(self.name)
            raise CreatorError(txt)

        self.data["members"] = [item.id]
        self.data["uuid"] = item.id  # for SubsetManager
        self.data["subset"] = (
            self.data["subset"]
            .replace(stub.PUBLISH_ICON, '')
            .replace(stub.LOADED_ICON, '')
        )

        stub.imprint(item, self.data)
        stub.set_label_color(item.id, 14)  # Cyan options 0 - 16
        stub.rename_item(item.id, stub.PUBLISH_ICON + self.data["subset"])
