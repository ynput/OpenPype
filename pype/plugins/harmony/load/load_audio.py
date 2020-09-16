from avalon import api, harmony


func = """
function getUniqueColumnName( column_prefix )
{
    var suffix = 0;
    // finds if unique name for a column
    var column_name = column_prefix;
    while(suffix < 2000)
    {
        if(!column.type(column_name))
        break;

        suffix = suffix + 1;
        column_name = column_prefix + "_" + suffix;
    }
    return column_name;
}

function func(args)
{
    var uniqueColumnName = getUniqueColumnName(args[0]);
    column.add(uniqueColumnName , "SOUND");
    column.importSound(uniqueColumnName, 1, args[1]);
}
func
"""


class ImportAudioLoader(api.Loader):
    """Import audio."""

    families = ["shot", "audio"]
    representations = ["wav"]
    label = "Import Audio"

    def load(self, context, name=None, namespace=None, data=None):
        wav_file = api.get_representation_path(context["representation"])
        harmony.send(
            {"function": func, "args": [context["subset"]["name"], wav_file]}
        )

        subset_name = context["subset"]["name"]

        return harmony.containerise(
            subset_name,
            namespace,
            subset_name,
            context,
            self.__class__.__name__
        )

    def update(self, container, representation):
        pass

    def remove(self, container):
        pass
