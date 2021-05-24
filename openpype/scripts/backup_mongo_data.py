import subprocess
import os
import click

@click.command()
@click.option("--mongo-uri", help="mongo db uri", default=None)
@click.option("--mongo-db-name", help="mongo db name", default=None)
@click.option(
    "--collections",
    help="collection string as ex: `project01|project02",
    default=None)
@click.option("--export-dir",
              help="Folder where should be saved all json files",
              default=None,
              type=click.Path())
def backup(mongo_uri, mongo_db_name, collections, export_dir):
    # input argument > mongo db url > mongodb+srv://user:password@mongodb.net
    # input argument > mongo db name > avalon
    # input argument > collections "project01|project02" (| slice to list)
    # input argument > export_dir
    assert any((mongo_uri, mongo_db_name, collections,
               export_dir)), "missing input arguments"

    # mongodb://<user>:<password>@<server>:<port>/<database>?authsource=admin
    # create cmd
    if "|" in collections:
        _collections = [c for c in collections.split("|")]
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
