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


class InvalidValueType(Exception):
    msg_template = "{}"

    def __init__(self, valid_types, invalid_type, path):
        msg = "Path \"{}\". ".format(path)

        joined_types = ", ".join(
            [str(valid_type) for valid_type in valid_types]
        )
        msg += "Got invalid type \"{}\". Expected: {}".format(
            invalid_type, joined_types
        )
        self.msg = msg
        super(InvalidValueType, self).__init__(msg)


class SchemaMissingFileInfo(Exception):
    def __init__(self, invalid):
        full_path_keys = []
        for item in invalid:
            full_path_keys.append("\"{}\"".format("/".join(item)))

        msg = (
            "Schema has missing definition of output file (\"is_file\" key)"
            " for keys. [{}]"
        ).format(", ".join(full_path_keys))
        super(SchemaMissingFileInfo, self).__init__(msg)


class SchemeGroupHierarchyBug(Exception):
    def __init__(self, entity_path):
        msg = (
            "Items with attribute \"is_group\" can't have another item with"
            " \"is_group\" attribute as child. Error happened in entity: {}"
        ).format(entity_path)
        super(SchemeGroupHierarchyBug, self).__init__(msg)


class SchemaDuplicatedKeys(Exception):
    def __init__(self, entity_path, key):
        msg = (
            "Schema item contain duplicated key \"{}\" in"
            " one hierarchy level. {}"
        ).format(key, entity_path)
        super(SchemaDuplicatedKeys, self).__init__(msg)


class SchemaDuplicatedEnvGroupKeys(Exception):
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


class SchemaTemplateMissingKeys(Exception):
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
