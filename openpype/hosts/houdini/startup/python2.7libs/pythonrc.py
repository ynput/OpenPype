from openpype.pipeline import install_host
from openpype.hosts.houdini import api


def main():
    print("Installing OpenPype ...")
    install_host(api)


main()
