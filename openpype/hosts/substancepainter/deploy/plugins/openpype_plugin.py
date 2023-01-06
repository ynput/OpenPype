
def start_plugin():
    from openpype.pipeline import install_host
    from openpype.hosts.substancepainter.api import SubstanceHost

    install_host(SubstanceHost())


def close_plugin():
    from openpype.pipeline import uninstall_host
    uninstall_host()


if __name__ == "__main__":
    start_plugin()
