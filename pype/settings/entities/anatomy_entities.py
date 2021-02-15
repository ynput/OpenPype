from .dict_immutable_keys_entity import DictImmutableKeysEntity
from .dict_mutable_keys_entity import DictMutableKeysEntity


class AnatomyEntity(DictImmutableKeysEntity):
    schema_types = ["anatomy"]


class AnatomyRootsEntity(DictMutableKeysEntity):
    schema_types = ["anatomy_roots"]
