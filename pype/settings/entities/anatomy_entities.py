from .dict_immutable_keys_entity import DictImmutableKeysEntity
from .dict_mutable_keys_entity import DictMutableKeysEntity


class AnatomyEntity(DictImmutableKeysEntity):
    schema_types = ["anatomy"]

    def _item_initalization(self):
        self._roots_entity = None
        self._templates_entity = None

        super(AnatomyEntity, self)._item_initalization()

    @property
    def roots_entity(self):
        if self._roots_entity is None:
            _roots_entity = None
            for child_entity in self.non_gui_children.values():
                if isinstance(child_entity, AnatomyRootsEntity):
                    _roots_entity = child_entity
                    break

            if _roots_entity is None:
                raise KeyError(
                    "AnatomyEntity does not contain AnatomyRootsEntity"
                )

            self._roots_entity = _roots_entity
        return self._roots_entity

    @property
    def templates_entity(self):
        if self._templates_entity is None:
            _templates_entity = None
            for child_entity in self.non_gui_children.values():
                if isinstance(child_entity, AnatomyTemplatesEntity):
                    _templates_entity = child_entity
                    break

            if _templates_entity is None:
                raise KeyError(
                    "AnatomyEntity does not contain AnatomyRootsEntity"
                )

            self._templates_entity = _templates_entity
        return self._templates_entity


class AnatomyRootsEntity(DictMutableKeysEntity):
    schema_types = ["anatomy_roots"]

    def schema_validations(self):
        if not isinstance(self.parent, AnatomyEntity):
            raise TypeError("Parent of {} is not AnatomyEntity object".format(
                self.__class__.__name__
            ))
        super(AnatomyRootsEntity, self).schema_validations()

    @property
    def has_studio_override(self):
        output = super(AnatomyRootsEntity, self).has_studio_override
        if not output:
            output = self.parent.templates_entity._child_has_studio_override
        return output

    @property
    def has_project_override(self):
        output = super(AnatomyRootsEntity, self).has_project_override
        if not output:
            output = self.parent.templates_entity._child_has_project_override
        return output


class AnatomyTemplatesEntity(DictImmutableKeysEntity):
    schema_types = ["anatomy_templates"]

    def schema_validations(self):
        if not isinstance(self.parent, AnatomyEntity):
            raise TypeError("Parent of {} is not AnatomyEntity object".format(
                self.__class__.__name__
            ))
        super(AnatomyTemplatesEntity, self).schema_validations()

    @property
    def has_studio_override(self):
        output = super(AnatomyTemplatesEntity, self).has_studio_override
        if not output:
            output = (
                self.parent.roots_entity._has_studio_override
                or self.parent.roots_entity._child_has_studio_override
            )
        return output

    @property
    def has_project_override(self):
        output = super(AnatomyTemplatesEntity, self).has_project_override
        if not output:
            output = (
                self.parent.roots_entity._has_project_override
                or self.parent.roots_entity._child_has_project_override
            )
        return output
