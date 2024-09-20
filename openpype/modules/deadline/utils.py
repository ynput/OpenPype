from openpype.pipeline.context_tools import (
    _get_modules_manager
)


def get_deadline_limit_groups(deadline_enabled, deadline_url, log):
    manager = _get_modules_manager()
    deadline_module = manager.modules_by_name["deadline"]

    limit_groups = []
    if deadline_enabled and deadline_url:
        requested_arguments = {"NamesOnly": True}
        limit_groups = deadline_module.get_deadline_data(
            deadline_url,
            "limitgroups",
            log=log,
            **requested_arguments
        )

    return limit_groups
