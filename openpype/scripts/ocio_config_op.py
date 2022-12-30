import click
import json
from pathlib2 import Path
import PyOpenColorIO as ocio


@click.group()
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
    config_path = Path(in_path)
    json_path = Path(out_path)
    print(config_path, json_path)
    if not config_path.is_file():
        raise IOError("Input path should be `config.ocio` file")

    config = ocio.Config().CreateFromFile(str(config_path))

    out_data = {
        c.getName(): c.getFamily()
        for c in config.getColorSpaces()
    }

    with open(json_path, "w") as f:
        json.dump(out_data, f)

    print(f"Data are saved to '{json_path}'")


@click.group()
def cli():
    pass


if __name__ == '__main__':
    cli.add_command(config)
    cli()
