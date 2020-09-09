from .lib import (
    apply_overrides,
    default_configuration,
    studio_system_configurations,
    studio_project_configurations,
    project_configurations_overrides
)


def system_configurations():
    default_values = default_configuration()["system_configurations"]
    studio_values = studio_system_configurations()
    return apply_overrides(default_values, studio_values)


def project_configurations(project_name):
    default_values = default_configuration()
    studio_values = studio_project_configurations()

    studio_overrides = apply_overrides(default_values, studio_values)

    project_overrides = project_configurations_overrides(project_name)

    return apply_overrides(studio_overrides, project_overrides)
