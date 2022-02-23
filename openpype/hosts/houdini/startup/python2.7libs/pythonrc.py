import avalon.api
from openpype.hosts.houdini import api


def main():
    print("Installing OpenPype ...")
    avalon.api.install(api)


main()
