import os

# Importing this takes a little over a second and thus this means
# that we have about 1.5 seconds delay before the workfile will actually
# be opened at the minimum
import openpype.hosts.resolve.api


def launch_menu():
    from openpype.pipeline import install_host
    print("Launching Resolve OpenPype menu..")

    # Activate resolve from openpype
    install_host(openpype.hosts.resolve.api)

    openpype.hosts.resolve.api.launch_pype_menu()


def open_file(path):
    # Avoid the need to "install" the host
    openpype.hosts.resolve.api.bmdvr = resolve  # noqa
    openpype.hosts.resolve.api.bmdvf = fusion  # noqa
    openpype.hosts.resolve.api.open_file(path)


def main():
    # Open last workfile
    workfile_path = os.environ.get("OPENPYPE_RESOLVE_OPEN_ON_LAUNCH")
    if workfile_path:
        open_file(workfile_path)
    else:
        print("No last workfile set to open. Skipping..")

    # Launch OpenPype menu
    # TODO: Add a setting to enable/disable this
    launch_menu()


if __name__ == "__main__":
    main()
