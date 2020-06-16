import os

import clique

from avalon import api, harmony

copy_files = """function copyFile(srcFilename, dstFilename)
{
    var srcFile = new PermanentFile(srcFilename);
    var dstFile = new PermanentFile(dstFilename);
    srcFile.copy(dstFile);
}
"""

import_files = """var PNGTransparencyMode = 0; //Premultiplied wih Black
var TGATransparencyMode = 0; //Premultiplied wih Black
var SGITransparencyMode = 0; //Premultiplied wih Black
var LayeredPSDTransparencyMode = 1; //Straight
var FlatPSDTransparencyMode = 2; //Premultiplied wih White

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

function import_files(args)
{
    var root = args[0];
    var files = args[1];
    var name = args[2];
    var start_frame = args[3];

    var vectorFormat = null;
    var extension = null;
    var filename = files[0];

    var pos = filename.lastIndexOf(".");
    if( pos < 0 )
        return null;

    extension = filename.substr(pos+1).toLowerCase();

    if(extension == "jpeg")
        extension = "jpg";
    if(extension == "tvg")
    {
        vectorFormat = "TVG"
        extension ="SCAN"; // element.add() will use this.
    }

    var elemId = element.add(
        name,
        "BW",
        scene.numberOfUnitsZ(),
        extension.toUpperCase(),
        vectorFormat
    );
    if (elemId == -1)
    {
        // hum, unknown file type most likely -- let's skip it.
        return null; // no read to add.
    }

    var uniqueColumnName = getUniqueColumnName(name);
    column.add(uniqueColumnName , "DRAWING");
    column.setElementIdOfDrawing(uniqueColumnName, elemId);

    var read = node.add(root, name, "READ", 0, 0, 0);
    var transparencyAttr = node.getAttr(
        read, frame.current(), "READ_TRANSPARENCY"
    );
    var opacityAttr = node.getAttr(read, frame.current(), "OPACITY");
    transparencyAttr.setValue(true);
    opacityAttr.setValue(true);

    var alignmentAttr = node.getAttr(read, frame.current(), "ALIGNMENT_RULE");
    alignmentAttr.setValue("ASIS");

    var transparencyModeAttr = node.getAttr(
        read, frame.current(), "applyMatteToColor"
    );
    if (extension == "png")
        transparencyModeAttr.setValue(PNGTransparencyMode);
    if (extension == "tga")
        transparencyModeAttr.setValue(TGATransparencyMode);
    if (extension == "sgi")
        transparencyModeAttr.setValue(SGITransparencyMode);
    if (extension == "psd")
        transparencyModeAttr.setValue(FlatPSDTransparencyMode);

    node.linkAttr(read, "DRAWING.ELEMENT", uniqueColumnName);

    // Create a drawing for each file.
    for( var i =0; i <= files.length - 1; ++i)
    {
        timing = start_frame + i
        // Create a drawing drawing, 'true' indicate that the file exists.
        Drawing.create(elemId, timing, true);
        // Get the actual path, in tmp folder.
        var drawingFilePath = Drawing.filename(elemId, timing.toString());
        copyFile( files[i], drawingFilePath );

        column.setEntry(uniqueColumnName, 1, timing, timing.toString());
    }
    return read;
}
import_files
"""

replace_files = """function replace_files(args)
{
    var files = args[0];
    var _node = args[1];
    var start_frame = args[2];

    var _column = node.linkedColumn(_node, "DRAWING.ELEMENT");

    // Delete existing drawings.
    var timings = column.getDrawingTimings(_column);
    for( var i =0; i <= timings.length - 1; ++i)
    {
        column.deleteDrawingAt(_column, parseInt(timings[i]));
    }

    // Create new drawings.
    for( var i =0; i <= files.length - 1; ++i)
    {
        timing = start_frame + i
        // Create a drawing drawing, 'true' indicate that the file exists.
        Drawing.create(node.getElementId(_node), timing, true);
        // Get the actual path, in tmp folder.
        var drawingFilePath = Drawing.filename(
            node.getElementId(_node), timing.toString()
        );
        copyFile( files[i], drawingFilePath );

        column.setEntry(_column, 1, timing, timing.toString());
    }
}
replace_files
"""


class ImageSequenceLoader(api.Loader):
    """Load images
    Stores the imported asset in a container named after the asset.
    """
    families = ["shot", "render"]
    representations = ["jpeg", "png"]

    def load(self, context, name=None, namespace=None, data=None):

        collections, remainder = clique.assemble(
            os.listdir(os.path.dirname(self.fname))
        )
        files = []
        for f in list(collections[0]):
            files.append(
                os.path.join(os.path.dirname(self.fname), f).replace("\\", "/")
            )

        read_node = harmony.send(
            {
                "function": copy_files + import_files,
                "args": ["Top", files, context["subset"]["name"], 1]
            }
        )["result"]

        self[:] = [read_node]

        return harmony.containerise(
            name,
            namespace,
            read_node,
            context,
            self.__class__.__name__
        )

    def update(self, container, representation):
        node = container.pop("node")

        collections, remainder = clique.assemble(
            os.listdir(
                os.path.dirname(api.get_representation_path(representation))
            )
        )
        files = []
        for f in list(collections[0]):
            files.append(
                os.path.join(os.path.dirname(self.fname), f).replace("\\", "/")
            )

        harmony.send(
            {
                "function": copy_files + replace_files,
                "args": [files, node, 1]
            }
        )

        harmony.imprint(
            node, {"representation": str(representation["_id"])}
        )

    def remove(self, container):
        node = container.pop("node")
        func = """function deleteNode(_node)
        {
            node.deleteNode(_node, true, true);
        }
        deleteNode
        """
        harmony.send(
            {"function": func, "args": [node]}
        )

    def switch(self, container, representation):
        self.update(container, representation)
