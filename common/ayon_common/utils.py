import os
import appdirs


def get_ayon_appdirs(*args):
    """Local app data directory of AYON client.

    Args:
        *args (Iterable[str]): Subdirectories/files in local app data dir.

    Returns:
        str: Path to directory/file in local app data dir.
    """

    return os.path.join(
        appdirs.user_data_dir("ayon", "ynput"),
        *args
    )


def _create_local_site_id():
    """Create a local site identifier."""
    from coolname import generate_slug

    new_id = generate_slug(3)

    print("Created local site id \"{}\"".format(new_id))

    return new_id


def get_local_site_id():
    """Get local site identifier.

    Site id is created if does not exist yet.
    """

    # used for background syncing
    site_id = os.environ.get("AYON_SITE_ID")
    if site_id:
        return site_id

    site_id_path = get_ayon_appdirs("site_id")
    if os.path.exists(site_id_path):
        with open(site_id_path, "r") as stream:
            site_id = stream.read()

    if not site_id:
        site_id = _create_local_site_id()
        with open(site_id_path, "w") as stream:
            stream.write(site_id)
    return site_id
