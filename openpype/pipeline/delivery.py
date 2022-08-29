"""Functions useful for delivery of published representations."""


def get_format_dict(anatomy, location_path):
    """Returns replaced root values from user provider value.

    Args:
        anatomy (Anatomy): Project anatomy.
        location_path (str): User provided value.

    Returns:
        (dict): Prepared data for formatting of a template.
    """

    format_dict = {}
    if not location_path:
        return format_dict

    location_path = location_path.replace("\\", "/")
    root_names = anatomy.root_names_from_templates(
        anatomy.templates["delivery"]
    )
    format_dict["root"] = {}
    for name in root_names:
        format_dict["root"][name] = location_path
    return format_dict
