import pyblish.api

from openpype.pipeline import (
    publish,
    PublishValidationError
)


class ValidateColorspaceLook(pyblish.api.InstancePlugin,
                             publish.OpenPypePyblishPluginMixin):
    """Validate colorspace look attributes"""

    label = "Validate colorspace look attributes"
    order = pyblish.api.ValidatorOrder
    hosts = ["traypublisher"]
    families = ["ociolook"]

    def process(self, instance):
        create_context = instance.context.data["create_context"]
        created_instance = create_context.get_instance_by_id(
            instance.data["instance_id"])
        creator_defs = created_instance.creator_attribute_defs

        ociolook_working_color = instance.data.get("ocioLookWorkingSpace")
        ociolook_items = instance.data.get("ocioLookItems", [])

        creator_defs_by_key = {_def.key: _def.label for _def in creator_defs}

        not_set_keys = {}
        if not ociolook_working_color:
            not_set_keys["working_colorspace"] = creator_defs_by_key[
                "working_colorspace"]

        for ociolook_item in ociolook_items:
            item_not_set_keys = self.validate_colorspace_set_attrs(
                ociolook_item, creator_defs_by_key)
            if item_not_set_keys:
                not_set_keys[ociolook_item["name"]] = item_not_set_keys

        if not_set_keys:
            message = (
                "Colorspace look attributes are not set: \n"
            )
            for key, value in not_set_keys.items():
                if isinstance(value, list):
                    values_string = "\n\t- ".join(value)
                    message += f"\n\t{key}:\n\t- {values_string}"
                else:
                    message += f"\n\t{value}"

            raise PublishValidationError(
                title="Colorspace Look attributes",
                message=message,
                description=message
            )

    def validate_colorspace_set_attrs(
        self,
        ociolook_item,
        creator_defs_by_key
    ):
        """Validate colorspace look attributes"""

        self.log.debug(f"Validate colorspace look attributes: {ociolook_item}")

        check_keys = [
            "input_colorspace",
            "output_colorspace",
            "direction",
            "interpolation"
        ]

        not_set_keys = []
        for key in check_keys:
            if ociolook_item[key]:
                # key is set and it is correct
                continue

            def_label = creator_defs_by_key.get(key)

            if not def_label:
                # raise since key is not recognized by creator defs
                raise KeyError(
                    f"Colorspace look attribute '{key}' is not "
                    f"recognized by creator attributes: {creator_defs_by_key}"
                )
            not_set_keys.append(def_label)

        return not_set_keys
