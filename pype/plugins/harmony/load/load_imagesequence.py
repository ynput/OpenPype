import os
import uuid

import clique

from avalon import api, harmony
import pype.lib

copy_files = """function copyFile(srcFilename, dstFilename)
{
    var srcFile = new PermanentFile(srcFilename);
    var dstFile = new PermanentFile(dstFilename);
    srcFile.copy(dstFile);
}
"""

import_files = """var PNGTransparencyMode = 1; //Premultiplied wih Black
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
    if (extension == "jpg")
        transparencyModeAttr.setValue(LayeredPSDTransparencyMode);

    node.linkAttr(read, "DRAWING.ELEMENT", uniqueColumnName);

    if (files.length == 1)
    {
        // Create a drawing drawing, 'true' indicate that the file exists.
        Drawing.create(elemId, 1, true);
        // Get the actual path, in tmp folder.
        var drawingFilePath = Drawing.filename(elemId, "1");
        copyFile(files[0], drawingFilePath);
        // Expose the image for the entire frame range.
        for( var i =0; i <= frame.numberOf() - 1; ++i)
        {
            timing = start_frame + i
            column.setEntry(uniqueColumnName, 1, timing, "1");
        }
    } else {
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
    }

    var green_color = new ColorRGBA(0, 255, 0, 255);
    node.setColor(read, green_color);

    return read;
}
import_files
"""

replace_files = """var PNGTransparencyMode = 1; //Premultiplied wih Black
var TGATransparencyMode = 0; //Premultiplied wih Black
var SGITransparencyMode = 0; //Premultiplied wih Black
var LayeredPSDTransparencyMode = 1; //Straight
var FlatPSDTransparencyMode = 2; //Premultiplied wih White

function replace_files(args)
{
    var files = args[0];
    MessageLog.trace(files);
    MessageLog.trace(files.length);
    var _node = args[1];
    var start_frame = args[2];

    var _column = node.linkedColumn(_node, "DRAWING.ELEMENT");
    var elemId = column.getElementIdOfDrawing(_column);

    // Delete existing drawings.
    var timings = column.getDrawingTimings(_column);
    for( var i =0; i <= timings.length - 1; ++i)
    {
        column.deleteDrawingAt(_column, parseInt(timings[i]));
    }


    var filename = files[0];
    var pos = filename.lastIndexOf(".");
    if( pos < 0 )
        return null;
    var extension = filename.substr(pos+1).toLowerCase();

    if(extension == "jpeg")
        extension = "jpg";

    var transparencyModeAttr = node.getAttr(
        _node, frame.current(), "applyMatteToColor"
    );
    if (extension == "png")
        transparencyModeAttr.setValue(PNGTransparencyMode);
    if (extension == "tga")
        transparencyModeAttr.setValue(TGATransparencyMode);
    if (extension == "sgi")
        transparencyModeAttr.setValue(SGITransparencyMode);
    if (extension == "psd")
        transparencyModeAttr.setValue(FlatPSDTransparencyMode);
    if (extension == "jpg")
        transparencyModeAttr.setValue(LayeredPSDTransparencyMode);

    if (files.length == 1)
    {
        // Create a drawing drawing, 'true' indicate that the file exists.
        Drawing.create(elemId, 1, true);
        // Get the actual path, in tmp folder.
        var drawingFilePath = Drawing.filename(elemId, "1");
        copyFile(files[0], drawingFilePath);
        MessageLog.trace(files[0]);
        MessageLog.trace(drawingFilePath);
        // Expose the image for the entire frame range.
        for( var i =0; i <= frame.numberOf() - 1; ++i)
        {
            timing = start_frame + i
            column.setEntry(_column, 1, timing, "1");
        }
    } else {
        // Create a drawing for each file.
        for( var i =0; i <= files.length - 1; ++i)
        {
            timing = start_frame + i
            // Create a drawing drawing, 'true' indicate that the file exists.
            Drawing.create(elemId, timing, true);
            // Get the actual path, in tmp folder.
            var drawingFilePath = Drawing.filename(elemId, timing.toString());
            copyFile( files[i], drawingFilePath );

            column.setEntry(_column, 1, timing, timing.toString());
        }
    }

    var green_color = new ColorRGBA(0, 255, 0, 255);
    node.setColor(_node, green_color);
}
replace_files
"""


class ImageSequenceLoader(api.Loader):
    """Load images
    Stores the imported asset in a container named after the asset.
    """
    families = ["shot", "render", "image", "plate", "reference"]
    representations = ["jpeg", "png", "jpg"]

    def load(self, context, name=None, namespace=None, data=None):

        collections, remainder = clique.assemble(
            os.listdir(os.path.dirname(self.fname))
        )
        files = []
        if collections:
            for f in list(collections[0]):
                files.append(
                    os.path.join(
                        os.path.dirname(self.fname), f
                    ).replace("\\", "/")
                )
        else:
            files.append(
                os.path.join(
                    os.path.dirname(self.fname), remainder[0]
                ).replace("\\", "/")
            )

        name = context["subset"]["name"]
        name += "_{}".format(uuid.uuid4())
        read_node = harmony.send(
            {
                "function": copy_files + import_files,
                "args": ["Top", files, name, 1]
            }
        )["result"]

        return harmony.containerise(
            name,
            namespace,
            read_node,
            context,
            self.__class__.__name__,
            nodes=[read_node]
        )

    def update(self, container, representation):
        node = harmony.find_node_by_name(container["name"], "READ")

        path = api.get_representation_path(representation)
        collections, remainder = clique.assemble(
            os.listdir(os.path.dirname(path))
        )
        files = []
        if collections:
            for f in list(collections[0]):
                files.append(
                    os.path.join(
                        os.path.dirname(path), f
                    ).replace("\\", "/")
                )
        else:
            files.append(
                os.path.join(
                    os.path.dirname(path), remainder[0]
                ).replace("\\", "/")
            )

        harmony.send(
            {
                "function": copy_files + replace_files,
                "args": [files, node, 1]
            }
        )

        # Colour node.
        func = """function func(args){
            for( var i =0; i <= args[0].length - 1; ++i)
            {
                var red_color = new ColorRGBA(255, 0, 0, 255);
                var green_color = new ColorRGBA(0, 255, 0, 255);
                if (args[1] == "red"){
                    node.setColor(args[0], red_color);
                }
                if (args[1] == "green"){
                    node.setColor(args[0], green_color);
                }
            }
        }
        func
        """
        if pype.lib.is_latest(representation):
            harmony.send({"function": func, "args": [node, "green"]})
        else:
            harmony.send({"function": func, "args": [node, "red"]})

        harmony.imprint(
            node, {"representation": str(representation["_id"])}
        )

    def remove(self, container):
        node = harmony.find_node_by_name(container["name"], "READ")

        func = """function deleteNode(_node)
        {
            node.deleteNode(_node, true, true);
        }
        deleteNode
        """
        harmony.send(
            {"function": func, "args": [node]}
        )
        harmony.imprint(node, {}, remove=True)

    def switch(self, container, representation):
        self.update(container, representation)
