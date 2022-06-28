import os
import re
import click

import speedcopy

from openpype.client import get_project, get_asset_by_name
from openpype.lib import Terminal
from openpype.api import Anatomy
from openpype.pipeline import legacy_io


t = Terminal()

texture_extensions = ['.tif', '.tiff', '.jpg', '.jpeg', '.tx', '.png', '.tga',
                      '.psd', '.dpx', '.hdr', '.hdri', '.exr', '.sxr', '.psb']


class TextureCopy:

    def __init__(self):
        if not legacy_io.Session:
            legacy_io.install()

    def _get_textures(self, path):
        textures = []
        for dir, subdir, files in os.walk(path):
            textures.extend(
                os.path.join(dir, x) for x in files
                if os.path.splitext(x)[1].lower() in texture_extensions)
        return textures

    def _get_destination_path(self, asset, project):
        project_name = project["name"]
        hierarchy = ""
        parents = asset['data']['parents']
        if parents and len(parents) > 0:
            hierarchy = os.path.join(*parents)

        template_data = {
            "project": {
                "name": project_name,
                "code": project['data']['code']
            },
            "asset": asset['name'],
            "family": 'texture',
            "subset": 'Main',
            "hierarchy": hierarchy
        }
        anatomy = Anatomy(project_name)
        anatomy_filled = anatomy.format(template_data)
        return anatomy_filled['texture']['path']

    def _get_version(self, path):
        versions = [0]
        dirs = [f.path for f in os.scandir(path) if f.is_dir()]
        for d in dirs:
            ver = re.search(r'^v(\d+)$',
                            os.path.basename(d),
                            flags=re.IGNORECASE)
            if ver is not None:
                versions.append(int(ver.group(1)))

        return max(versions) + 1

    def _copy_textures(self, textures, destination):
        for tex in textures:
            dst = os.path.join(destination,
                               os.path.basename(tex))
            t.echo("  - Copy {} -> {}".format(tex, dst))
            try:
                speedcopy.copyfile(tex, dst)
            except Exception as e:
                t.echo("!!! Copying failed")
                t.echo("!!! {}".format(e))
                exit(1)

    def process(self, asset_name, project_name, path):
        """
        Process all textures found in path and copy them to asset under
        project.
        """

        t.echo(">>> Looking for textures ...")
        textures = self._get_textures(path)
        if len(textures) < 1:
            t.echo("!!! no textures found.")
            exit(1)
        else:
            t.echo(">>> Found {} textures ...".format(len(textures)))

        project = get_project(project_name)
        if not project:
            t.echo("!!! Project name [ {} ] not found.".format(project_name))
            exit(1)

        asset = get_asset_by_name(project_name, asset_name)
        if not asset:
            t.echo("!!! Asset [ {} ] not found in project".format(asset_name))
            exit(1)
        t.echo((">>> Project [ {} ] and "
                "asset [ {} ] seems to be OK ...").format(project['name'],
                                                          asset['name']))

        dst_path = self._get_destination_path(asset, project)
        t.echo("--- Using [ {} ] as destination path".format(dst_path))
        if not os.path.exists(dst_path):
            try:
                os.makedirs(dst_path)
            except IOError as e:
                t.echo("!!! Unable to create destination directory")
                t.echo("!!! {}".format(e))
                exit(1)
        version = '%02d' % self._get_version(dst_path)
        t.echo("--- Using version [ {} ]".format(version))
        dst_path = os.path.join(dst_path, "v{}".format(version))
        t.echo("--- Final destination path [ {} ]".format(dst_path))
        try:
            os.makedirs(dst_path)
        except FileExistsError:
            t.echo("!!! Somethings wrong, version directory already exists")
            exit(1)
        except IOError as e:
            t.echo("!!! Cannot create version directory")
            t.echo("!!! {}".format(e))
            exit(1)

        t.echo(">>> copying textures  ...")
        self._copy_textures(textures, dst_path)
        t.echo(">>> done.")
        t.echo("<<< terminating ...")


@click.command()
@click.option('--asset', required=True)
@click.option('--project', required=True)
@click.option('--path', required=True)
def texture_copy(asset, project, path):
    t.echo("*** Running Texture tool ***")
    t.echo(">>> Initializing avalon session ...")
    os.environ["AVALON_PROJECT"] = project
    os.environ["AVALON_ASSET"] = asset
    TextureCopy().process(asset, project, path)


if __name__ == '__main__':
    texture_copy()
