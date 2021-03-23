from .dict_immutable_keys_entity import DictImmutableKeysEntity
from .lib import OverrideState


class AnatomyEntity(DictImmutableKeysEntity):
    schema_types = ["anatomy"]

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
