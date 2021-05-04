def is_password_required():
    from openpype.settings import (
        get_system_settings,
        get_local_settings
    )

    system_settings = get_system_settings()
    password = system_settings["general"].get("admin_password")
    if not password:
        return False

    local_settings = get_local_settings()
    is_admin = local_settings.get("general", {}).get("is_admin", False)
    if is_admin:
        return False
    return True
