from openpype.settings.lib import get_system_settings
from .dict_immutable_keys_entity import DictImmutableKeysEntity
from .lib import OverrideState
from .exceptions import EntitySchemaError


class AnatomyEntity(DictImmutableKeysEntity):
    schema_types = ["anatomy"]

    def _item_initialization(self):
        super(AnatomyEntity, self)._item_initialization()

        # Set (if requested) the Attributes widget/section in read-only
        # This feature exists to add protection on the attributes synced with
        # prod tracker (Shotgrid, Ftrack, Kitsu, ...)
        # Anatomy Attributes should only be edited on the prod tracker side, then
        # the sync will retrieve and update the OpenPype data for the project.
        system_settings = get_system_settings()
        protect_attrs = system_settings["general"].get("project", {}).get("protect_anatomy_attributes", False)
        self.non_gui_children["attributes"].protect_attrs = protect_attrs
        if protect_attrs:
            self.non_gui_children["attributes"].read_only = protect_attrs

    def _update_current_metadata(self):
        if self._override_state is OverrideState.PROJECT:
            return {}
        return super(AnatomyEntity, self)._update_current_metadata()

    def set_override_state(self, *args, **kwargs):
        super(AnatomyEntity, self).set_override_state(*args, **kwargs)
        if self._override_state is OverrideState.PROJECT:
            for child_obj in self.non_gui_children.values():
                if not child_obj.has_project_override:
                    self.add_to_project_override()
                    break

    def on_child_change(self, child_obj):
        if self._override_state is OverrideState.PROJECT:
            if not child_obj.has_project_override:
                child_obj.add_to_project_override()
        return super(AnatomyEntity, self).on_child_change(child_obj)

    def schema_validations(self):
        non_group_children = []
        for key, child_obj in self.non_gui_children.items():
            if not child_obj.is_group:
                non_group_children.append(key)

        if non_group_children:
            _non_group_children = [
                "project_anatomy/{}".format(key)
                for key in non_group_children
            ]
            reason = (
                "Anatomy must have all children as groups."
                " Set 'is_group' to `true` on > {}"
            ).format(", ".join([
                '"{}"'.format(item)
                for item in _non_group_children
            ]))
            raise EntitySchemaError(self, reason)

        return super(AnatomyEntity, self).schema_validations()
