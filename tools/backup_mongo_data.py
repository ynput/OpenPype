import subprocess
import os
import click


@click.command()
@click.option("--mongo-db-name", help="mongo db name", default=None)
@click.option(
    "--collections",
    help="collection string as ex: `project01|project02",
    default=None)
@click.option("--export-dir",
              help="Folder where should be saved all json files",
              default=None,
              type=click.Path())
def backup(mongo_db_name, collections, export_dir):
    """Backup OpenPype mongo db data

    Args:
        mongo_db_name (str): name of openpype database
        collections (str): names of collections separated by `|` (no spaces)
        export_dir (str): path pointing to directory of export
    """
    mongo_uri = os.getenv("OPENPYPE_MONGO")

    assert any((mongo_uri, mongo_db_name, collections,
               export_dir)), "missing input arguments"

    if "|" in collections:
        _collections = [c for c in collections.split("|")]
    elif isinstance(collections, list):
        _collections = collections
    else:
        _collections = [collections]

    for collection in _collections:
        cmd_data = {
            "uri": mongo_uri,
            "dbName": mongo_db_name,
            "collection": collection,
            "fpath": os.path.join(export_dir, "{}.json".format(collection))
        }
        cmd = (
            "mongoexport --uri=\"{uri}/{dbName}?authsource=admin\" "
            "--collection=\"{collection}\" "
            "--out=\"{fpath}\"").format(**cmd_data)

        print(cmd)

        pout = subprocess.Popen(
            cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True)

        output, errors = pout.communicate()

        if errors:
            print(errors)
        else:
            print(output)


if __name__ == '__main__':
    backup()
