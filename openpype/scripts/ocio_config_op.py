import click
import json
from pathlib2 import Path
import PyOpenColorIO as ocio


@click.group()
def main():
    pass


@main.group()
def config():
    pass


@config.command(
    name="get_colorspace",
    help=(
        "return all colorspaces from config file "
        "--path input arg is required"
    )
)
@click.option("--in_path", required=True,
              help="path where to read ocio config file",
              type=click.Path(exists=True))
@click.option("--out_path", required=True,
              help="path where to write output json file",
              type=click.Path())
def get_colorspace(in_path, out_path):
    json_path = Path(out_path)

    out_data = get_colorspace_data(in_path)

    with open(json_path, "w") as f:
        json.dump(out_data, f)

    print(f"Colorspace data are saved to '{json_path}'")


def get_colorspace_data(config_path):
    config_path = Path(config_path)

    if not config_path.is_file():
        raise IOError(f"Input path `{config_path}` should be `config.ocio` file")

    config = ocio.Config().CreateFromFile(str(config_path))

    return {
        c.getName(): c.getFamily()
        for c in config.getColorSpaces()
    }


@config.command(
    name="get_views",
    help=(
        "return all viewers from config file "
        "--path input arg is required"
    )
)
@click.option("--in_path", required=True,
              help="path where to read ocio config file",
              type=click.Path(exists=True))
@click.option("--out_path", required=True,
              help="path where to write output json file",
              type=click.Path())
def get_views(in_path, out_path):
    json_path = Path(out_path)

    out_data = get_views_data(in_path)

    with open(json_path, "w") as f:
        json.dump(out_data, f)

    print(f"Viewer data are saved to '{json_path}'")


def get_views_data(config_path):

    config_path = Path(config_path)

    if not config_path.is_file():
        raise IOError("Input path should be `config.ocio` file")

    config = ocio.Config().CreateFromFile(str(config_path))

    return {
        f"{d}/{v}": {"display": d, "view": v}
        for d in config.getDisplays()
        for v in config.getViews(d)
    }


if __name__ == '__main__':
    main()
