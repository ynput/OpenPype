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

        ociolook_items = instance.data.get("ocioLookItems", [])

        for ociolook_item in ociolook_items:
            self.validate_colorspace_set_attrs(ociolook_item, creator_defs)

    def validate_colorspace_set_attrs(self, ociolook_item, creator_defs):
        """Validate colorspace look attributes"""

        self.log.debug(f"Validate colorspace look attributes: {ociolook_item}")
        self.log.debug(f"Creator defs: {creator_defs}")

        check_keys = [
            "working_colorspace",
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

            def_label = next(
                (d_.label for d_ in creator_defs if key == d_.key),
                None
            )
            if not def_label:
                def_attrs = [(d_.key, d_.label) for d_ in creator_defs]
                # raise since key is not recognized by creator defs
                raise KeyError(
                    f"Colorspace look attribute '{key}' is not "
                    f"recognized by creator attributes: {def_attrs}"
                )
            not_set_keys.append(def_label)

        if not_set_keys:
            message = (
                "Colorspace look attributes are not set: "
                f"{', '.join(not_set_keys)}"
            )
            raise PublishValidationError(
                title="Colorspace Look attributes",
                message=message,
                description=message
            )
