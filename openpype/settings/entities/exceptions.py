from openpype.settings.constants import KEY_ALLOWED_SYMBOLS


class DefaultsNotDefined(Exception):
    def __init__(self, obj):
        msg = "Default values for object are not set. {}".format(obj.path)
        super(DefaultsNotDefined, self).__init__(msg)


class StudioDefaultsNotDefined(Exception):
    def __init__(self, obj):
        msg = "Studio default values for object are not set. {}".format(
            obj.path
        )
        super(StudioDefaultsNotDefined, self).__init__(msg)


class BaseInvalidValue(Exception):
    def __init__(self, reason, path):
        msg = "Path \"{}\". {}".format(path, reason)
        self.msg = msg
        super(BaseInvalidValue, self).__init__(msg)


class InvalidValueType(BaseInvalidValue):
    def __init__(self, valid_types, invalid_type, path):
        joined_types = ", ".join(
            [str(valid_type) for valid_type in valid_types]
        )
        msg = "Got invalid type \"{}\". Expected: {}".format(
            invalid_type, joined_types
        )
        super(InvalidValueType, self).__init__(msg, path)


class RequiredKeyModified(KeyError):
    def __init__(self, entity_path, key):
        msg = "{} - Tried to modify required key \"{}\"."
        super(RequiredKeyModified, self).__init__(msg.format(entity_path, key))


class InvalidKeySymbols(KeyError):
    def __init__(self, entity_path, key):
        msg = "{} - Invalid key \"{}\". Allowed symbols are {}"
        super(InvalidKeySymbols, self).__init__(
            msg.format(entity_path, key, KEY_ALLOWED_SYMBOLS)
        )


class SchemaError(Exception):
    pass


class EntitySchemaError(SchemaError):
    def __init__(self, entity, reason):
        self.entity = entity
        self.reason = reason
        msg = "{} {} - {}".format(entity.__class__, entity.path, reason)
        super(EntitySchemaError, self).__init__(msg)


class SchemeGroupHierarchyBug(EntitySchemaError):
    def __init__(self, entity):
        reason = (
            "Items with attribute \"is_group\" can't have another item with"
            " \"is_group\" attribute as child."
        )
        super(SchemeGroupHierarchyBug, self).__init__(entity, reason)


class SchemaMissingFileInfo(SchemaError):
    def __init__(self, invalid):
        full_path_keys = []
        for item in invalid:
            full_path_keys.append("\"{}\"".format("/".join(item)))

        msg = (
            "Schema has missing definition of output file (\"is_file\" key)"
            " for keys. [{}]"
        ).format(", ".join(full_path_keys))
        super(SchemaMissingFileInfo, self).__init__(msg)


class SchemaDuplicatedKeys(SchemaError):
    def __init__(self, entity, key):
        msg = (
            "Schema item contain duplicated key \"{}\" in"
            " one hierarchy level."
        ).format(key)
        super(SchemaDuplicatedKeys, self).__init__(entity, msg)


class SchemaDuplicatedEnvGroupKeys(SchemaError):
    def __init__(self, invalid):
        items = []
        for key_path, keys in invalid.items():
            joined_keys = ", ".join([
                "\"{}\"".format(key) for key in keys
            ])
            items.append("\"{}\" ({})".format(key_path, joined_keys))

        msg = (
            "Schema items contain duplicated environment group keys. {}"
        ).format(" || ".join(items))
        super(SchemaDuplicatedEnvGroupKeys, self).__init__(msg)


class SchemaTemplateMissingKeys(SchemaError):
    def __init__(self, missing_keys, required_keys, template_name=None):
        self.missing_keys = missing_keys
        self.required_keys = required_keys
        if template_name:
            msg = "Schema template \"{}\" require more keys.\n".format(
                template_name
            )
        else:
            msg = ""
        msg += "Required keys: {}\nMissing keys: {}".format(
            self.join_keys(required_keys),
            self.join_keys(missing_keys)
        )
        super(SchemaTemplateMissingKeys, self).__init__(msg)

    def join_keys(self, keys):
        return ", ".join([
            "\"{}\"".format(key) for key in keys
        ])
